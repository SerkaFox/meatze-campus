import fs from "fs";
import * as acorn from "acorn";
import * as walk from "acorn-walk";

const code = fs.readFileSync(process.argv[2], "utf8");
const file = process.argv[2];

let ast;
try {
  ast = acorn.parse(code, {
    ecmaVersion: "latest",
    sourceType: "script",
    allowHashBang: true,
    locations: true
  });
} catch (e) {
  ast = acorn.parse(code, {
    ecmaVersion: "latest",
    sourceType: "module",
    allowHashBang: true,
    locations: true
  });
}

const functions = [];
const calls = [];
const callsSignificant = [];
const domSelectors = new Set();
const events = new Set();
const globals = new Set();
const stringLiterals = new Set();

const selectorAliases = new Set(); // $ / $$ ... detectados
const apiBases = {};               // {"API_BASE": "/meatze/v5", "API_A": "/meatze/v5/admin", ...}

function paramToStr(p) {
  if (!p) return null;
  if (p.type === "Identifier") return p.name;
  if (p.type === "AssignmentPattern") return `${paramToStr(p.left)}=...`;
  if (p.type === "RestElement") return `...${paramToStr(p.argument)}`;
  if (p.type === "ObjectPattern") {
    const keys = [];
    for (const prop of p.properties || []) {
      if (prop.type === "Property") {
        if (prop.key?.type === "Identifier") keys.push(prop.key.name);
        else keys.push("{prop}");
      } else if (prop.type === "RestElement") keys.push("...rest");
    }
    return `{${keys.join(",")}}`;
  }
  if (p.type === "ArrayPattern") return `[...]`;
  return p.type;
}

function addPatternNames(pattern, outSet) {
  if (!pattern) return;
  if (pattern.type === "Identifier") outSet.add(pattern.name);
  else if (pattern.type === "ObjectPattern") {
    for (const prop of pattern.properties || []) {
      if (prop.type === "Property") addPatternNames(prop.value, outSet);
      else if (prop.type === "RestElement") addPatternNames(prop.argument, outSet);
    }
  } else if (pattern.type === "ArrayPattern") {
    for (const el of pattern.elements || []) addPatternNames(el, outSet);
  } else if (pattern.type === "AssignmentPattern") addPatternNames(pattern.left, outSet);
  else if (pattern.type === "RestElement") addPatternNames(pattern.argument, outSet);
}

function literalOrTemplateRaw(node) {
  if (!node) return null;
  if (node.type === "Literal" && typeof node.value === "string") return node.value;
  if (node.type === "TemplateLiteral") return code.slice(node.start, node.end);
  return null;
}

function isTopLevel(node) {
  // acorn-walk simple не даёт parent, поэтому globals берём из ast.body отдельно
  return false;
}

function getPseudoTopLevelBody(ast) {
  // если файл обёрнут в (()=>{ ... })() или (function(){ ... })()
  if (ast.body?.length === 1 && ast.body[0].type === "ExpressionStatement") {
    const expr = ast.body[0].expression;
    if (expr?.type === "CallExpression") {
      const callee = expr.callee;
      if (callee?.type === "ArrowFunctionExpression" || callee?.type === "FunctionExpression") {
        if (callee.body?.type === "BlockStatement") return callee.body.body; // массив Statement
      }
    }
  }
  return ast.body || [];
}

function collectStringLiterals(node, out=[]) {
  if (!node) return out;
  if (node.type === "Literal" && typeof node.value === "string") out.push(node.value);
  if (node.type === "TemplateLiteral") out.push(code.slice(node.start, node.end));
  for (const k of Object.keys(node)) {
    const v = node[k];
    if (v && typeof v === "object") {
      if (Array.isArray(v)) v.forEach(x => collectStringLiterals(x, out));
      else collectStringLiterals(v, out);
    }
  }
  return out;
}

// === GLOBALS + API BASES (top-level) ===
const topBody = getPseudoTopLevelBody(ast);
for (const node of topBody) {
  if (node.type === "VariableDeclaration") {
    for (const d of node.declarations) {
      addPatternNames(d.id, globals);

      // detect api bases: const API_BASE = ".../meatze/v5"  |  const API_A = API_BASE + "/admin" (template will be captured raw)
		if (d.id?.type === "Identifier" && d.init) {
		  const name = d.id.name;

		  const raw = literalOrTemplateRaw(d.init);
		  if (raw && (raw.includes("/meatze") || raw.includes("/v5") || raw.includes("/admin"))) {
			apiBases[name] = raw;
		  } else if (d.init.type === "BinaryExpression" || d.init.type === "LogicalExpression") {
			// fallback: keep raw slice if it includes meatze or API_BASE/API_A
			const slice = code.slice(d.init.start, d.init.end);
			if (slice.includes("/meatze") || slice.includes("API_BASE") || slice.includes("API_A") || slice.includes("/v5") || slice.includes("/admin")) {
			  apiBases[name] = slice;
			}
		  } else {
			// generic scan: if expression contains route strings, keep raw expression slice
			const parts = collectStringLiterals(d.init, []);
			const joined = parts.join(" ");
			if (joined.includes("/meatze") || joined.includes("/v5") || joined.includes("/admin")) {
			  apiBases[name] = code.slice(d.init.start, d.init.end);
			}
		  }
		}

    }
  }
  if (node.type === "FunctionDeclaration" && node.id?.name) globals.add(node.id.name);
}


// === WALK ===
walk.simple(ast, {
  FunctionDeclaration(node) {
    functions.push({
      name: node.id ? node.id.name : null,
      type: "function",
      params: node.params.map(paramToStr),
      loc: { start: { line: node.loc.start.line } }
    });
  },

  VariableDeclarator(node) {
    // Detect alias: const $ = s => document.querySelector(s)
    if (node.id?.type === "Identifier" && node.init?.type === "ArrowFunctionExpression") {
      const name = node.id.name;
      const body = node.init.body;

      if (
        body?.type === "CallExpression" &&
        body.callee?.type === "MemberExpression" &&
        body.callee.object?.type === "Identifier" &&
        body.callee.object.name === "document" &&
        body.callee.property?.type === "Identifier" &&
        (body.callee.property.name === "querySelector" || body.callee.property.name === "querySelectorAll")
      ) {
        selectorAliases.add(name);
      }
    }

    // Function assigned: const x = (...) => {} / function(){}
    if (node.init && (node.init.type === "ArrowFunctionExpression" || node.init.type === "FunctionExpression")) {
      functions.push({
        name: node.id?.name || null,
        type: node.init.type === "ArrowFunctionExpression" ? "arrow" : "function_expr",
        params: (node.init.params || []).map(paramToStr),
        loc: { start: { line: node.loc.start.line } }
      });
    }
  },

  Literal(n) {
    if (typeof n.value === "string") stringLiterals.add(n.value);
  },

  CallExpression(node) {
    let callee = null;
    if (node.callee.type === "Identifier") callee = node.callee.name;
    else if (node.callee.type === "MemberExpression" && node.callee.property.type === "Identifier") callee = node.callee.property.name;

    const args = node.arguments.map(a => {
      if (a.type === "Literal") return a.value;
      if (a.type === "TemplateLiteral") return { __template: code.slice(a.start, a.end) };
      return null;
    });

    const rec = { callee, args, line: node.loc.start.line };
    calls.push(rec);

    // Significant calls only
    if (["fetch", "apiJSON", "addEventListener", "dispatchEvent"].includes(callee)) {
      callsSignificant.push(rec);
    }

    // DOM direct: document.getElementById / querySelector / querySelectorAll
    if (
      node.callee.type === "MemberExpression" &&
      node.callee.object.type === "Identifier" &&
      node.callee.object.name === "document" &&
      node.callee.property.type === "Identifier"
    ) {
      const m = node.callee.property.name;
      const a0 = node.arguments?.[0];

      if (a0?.type === "Literal" && typeof a0.value === "string") {
        if (m === "getElementById") domSelectors.add("#" + a0.value);
        if (m === "querySelector" || m === "querySelectorAll") domSelectors.add(a0.value);
      }
    }

    // Alias selectors: $(...)
    if (callee && selectorAliases.has(callee)) {
      const a0 = node.arguments?.[0];
      if (a0?.type === "Literal" && typeof a0.value === "string") domSelectors.add(a0.value);
    }

	if (
	  node.callee.type === "MemberExpression" &&
	  node.callee.property.name === "dispatchEvent"
	) {
	  const a0 = node.arguments?.[0];
	  if (a0?.type === "NewExpression" && a0.callee?.name === "CustomEvent") {
		const evName = a0.arguments?.[0];
		if (evName?.type === "Literal") events.add(`${evName.value} @ line ${node.loc.start.line} (dispatchEvent)`);
	  }
	}

    // Event listeners: el.addEventListener("click", ...)
    if (
      node.callee.type === "MemberExpression" &&
      node.callee.property.name === "addEventListener"
    ) {
      const evt = node.arguments[0];
      if (evt?.type === "Literal") events.add(`${evt.value} @ line ${node.loc.start.line}`);
    }
  }
});

// === ENDPOINTS STRICT ===
const endpoints = new Set();          // literal strings that look like paths
const endpointsTemplates = new Set(); // raw template literals used as first arg in fetch/apiJSON/api
const endpointsParts = new Set();     // strings in code that look like route fragments

for (const c of callsSignificant) {
  if (!["fetch", "apiJSON", "api"].includes(c.callee)) continue;
  const arg = c.args?.[0];

  if (typeof arg === "string") {
    if (arg.startsWith("/") || arg.includes("/meatze")) endpoints.add(arg);
  } else if (arg && typeof arg === "object" && arg.__template) {
    const t = arg.__template;
    // keep only templates that likely are URLs
    if (t.includes("/") && (t.includes("/meatze") || t.includes("API_BASE") || t.includes("API_A") || t.includes("/curso/") || t.includes("/admin"))) {
      endpointsTemplates.add(t);
    }
  }
}

// Parts from string literals (strict facts)
for (const s of stringLiterals) {
  if (typeof s !== "string") continue;
  if (s.startsWith("/")) endpointsParts.add(s);
  else if (s.includes("/meatze") || s.includes("/v5") || s.includes("/admin") || s.includes("/curso") || s.includes("/horario")) endpointsParts.add(s);
}

console.log(JSON.stringify({
  file,
  functions,
  callsSignificant,
  domSelectors: [...domSelectors],
  events: [...events],
  globals: [...globals],
  stringLiterals: [...stringLiterals],
  selectorAliases: [...selectorAliases],
  apiBases,
  endpoints: [...endpoints],
  endpointsTemplates: [...endpointsTemplates],
  endpointsParts: [...endpointsParts]
}, null, 2));
