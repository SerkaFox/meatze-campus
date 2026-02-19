# panel/jitsi_live_watch.py

import re
import subprocess
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from api.models import Curso

ROOM_RE = re.compile(r'\b(meatze-\d+-[a-z0-9-]+)\b')

# Эти паттерны ты подгонишь по факту, но базово так:
OPEN_HINTS  = ("Created conference", "created room", "Created MUC", "conference created", "joined", "Focus joined")
CLOSE_HINTS = ("Destroyed conference", "destroyed room", "room destroyed", "conference destroyed", "last occupant", "closing")

class Command(BaseCommand):
    help = "Watch Jitsi/Prosody logs and toggle Curso.live_is_open"

    def add_arguments(self, parser):
        parser.add_argument("--domain", default="meetjwt.meatzeaula.es")
        parser.add_argument("--services", nargs="*", default=["jicofo", "prosody"])
        parser.add_argument("--close-idle-seconds", type=int, default=60)  # страховка

    def handle(self, *args, **opts):
        services = opts["services"]
        close_idle = opts["close_idle_seconds"]

        # journalctl -f по нескольким юнитам
        cmd = ["journalctl", "-f", "-n", "0", "-o", "cat"]
        for s in services:
            cmd += ["-u", s]

        self.stdout.write(self.style.SUCCESS(f"[watch] starting: {' '.join(cmd)}"))

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        last_open_seen = {}  # room -> ts

        for line in p.stdout:
            line = line.strip()
            if not line:
                continue

            m = ROOM_RE.search(line)
            if not m:
                continue

            room = m.group(1)
            now = timezone.now()

            # heartbeat
            last_open_seen[room] = now

            # Решаем open/close по ключевым словам
            is_open_event = any(h.lower() in line.lower() for h in OPEN_HINTS)
            is_close_event = any(h.lower() in line.lower() for h in CLOSE_HINTS)

            # Если в логах есть явное destroyed — закрываем
            if is_close_event:
                self._set_live(room, False, now, line)
                continue

            # Иначе если есть явное created/joined — открываем
            if is_open_event:
                self._set_live(room, True, now, line)

            # страховка: если долго нет сигналов по комнате — закрыть
            # (полезно, если destroyed не попадает в логи)
            self._close_idle(last_open_seen, close_idle)

    def _close_idle(self, last_open_seen, close_idle):
        now = timezone.now()
        for room, ts in list(last_open_seen.items()):
            if (now - ts).total_seconds() > close_idle:
                # нет сигналов -> считаем, что конфа умерла
                self._set_live(room, False, now, reason="idle-timeout")
                last_open_seen.pop(room, None)

    @transaction.atomic
    def _set_live(self, room: str, open_flag: bool, now, reason):
        # room начинается с meatze-<curso_id>-...
        try:
            parts = room.split("-")
            curso_id = int(parts[1])
        except Exception:
            return

        try:
            curso = Curso.objects.select_for_update().get(id=curso_id)
        except Curso.DoesNotExist:
            return

        changed = False

        if open_flag and not curso.live_is_open:
            curso.live_is_open = True
            curso.live_opened_at = now
            curso.live_closed_at = None
            changed = True

        if (not open_flag) and curso.live_is_open:
            curso.live_is_open = False
            curso.live_closed_at = now
            changed = True

        curso.live_last_signal_at = now
        curso.save(update_fields=["live_is_open", "live_opened_at", "live_closed_at", "live_last_signal_at"])

        if changed:
            print(f"[live] curso={curso.id} room={room} -> {'OPEN' if open_flag else 'CLOSE'} reason={reason}")