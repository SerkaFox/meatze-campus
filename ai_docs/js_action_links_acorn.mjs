import fs from "fs";
import * as acorn from "acorn";
import * as walk from "acorn-walk";

const file = process.argv[2];
const code = fs.readFileSync(file, "utf8");
const idToSelector = new Map();
let ast;
try {
  ast = acorn.parse(code, { ecmaVersion: "latest", sourceType: "script", allowHashBang: true, locations: true });
} catch {
  ast = acorn.parse(code, { ecmaVersion: "latest", sourceType: "module", allowHashBang: true, locations: true });
}

// detect selector aliases like: const $ = s => document.querySelector(s)
const selectorAliases = new Set();

function getPseudoTopLevelBody(ast) {
  if (ast.body?.length === 1 && ast.body[0].type === "ExpressionStatement") {
    const expr = ast.body[0].expression;
    if (expr?.type === "CallExpression") {
      const callee = expr.callee;
      if ((callee?.type === "ArrowFunctionExpression" || callee?.type === "FunctionExpression") && callee.body?.type === "BlockStatement") {
        return callee.body.body;
      }
    }
  }
  return ast.body || [];
}

const topBody = getPseudoTopLevelBody(ast);
for (const node of topBody) {
  if (node.type === "VariableDeclaration") {
    for (const d of node.declarations || []) {
      if (d.id?.type === "Identifier" && d.init?.type === "ArrowFunctionExpression") {
        const name = d.id.name;
        const body = d.init.body;
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
    }
  }
}

function selFromNode(n) {
  if (!n) return null;

  // document.getElementById("x") => #x
  if (n.type === "CallExpression" && n.callee?.type === "MemberExpression") {
    const obj = n.callee.object;
    const prop = n.callee.property;
    if (obj?.type === "Identifier" && obj.name === "document" && prop?.type === "Identifier") {
      const a0 = n.arguments?.[0];
      if (a0?.type === "Literal" && typeof a0.value === "string") {
        if (prop.name === "getElementById") return "#" + a0.value;
        if (prop.name === "querySelector" || prop.name === "querySelectorAll") return a0.value;
      }
    }
  }

  // $("...") where $ is alias
  if (n.type === "CallExpression" && n.callee?.type === "Identifier" && selectorAliases.has(n.callee.name)) {
    const a0 = n.arguments?.[0];
    if (a0?.type === "Literal" && typeof a0.value === "string") return a0.value;
  }

  return null;
}

function learnSelectorAssignment(node) {
  // const x = document.querySelector("...") | getElementById("...") | $("...")
  if (!node || node.type !== "VariableDeclarator") return;
  if (node.id?.type !== "Identifier") return;

  const name = node.id.name;
  const init = node.init;
  if (!init) return;

  // document.querySelector / querySelectorAll / getElementById
  if (init.type === "CallExpression" && init.callee?.type === "MemberExpression") {
    const obj = init.callee.object;
    const prop = init.callee.property;
    if (obj?.type === "Identifier" && obj.name === "document" && prop?.type === "Identifier") {
      const a0 = init.arguments?.[0];
      if (a0?.type === "Literal" && typeof a0.value === "string") {
        if (prop.name === "getElementById") {
          idToSelector.set(name, "#" + a0.value);
          return;
        }
        if (prop.name === "querySelector" || prop.name === "querySelectorAll") {
          idToSelector.set(name, a0.value);
          return;
        }
      }
    }
  }

  // $("...") where $ is alias
  if (init.type === "CallExpression" && init.callee?.type === "Identifier" && selectorAliases.has(init.callee.name)) {
    const a0 = init.arguments?.[0];
    if (a0?.type === "Literal" && typeof a0.value === "string") {
      idToSelector.set(name, a0.value);
      return;
    }
  }
}


function argToStrOrTemplate(a) {
  if (!a) return null;
  if (a.type === "Literal") return a.value;
  if (a.type === "TemplateLiteral") return code.slice(a.start, a.end);
  return null;
}

function collectHandlerHints(fnNode) {
  // Strict hints extracted from handler internals:
  // - selectorHints: from e.target.matches("...") / closest("...")
  // - calls/endpoints: from fetch/apiJSON/api inside handler
  const calls = new Set();
  const endpoints = new Set();
  const endpointsTemplates = new Set();
  const selectorHints = new Set();

  walk.simple(fnNode, {
    CallExpression(n) {
      // callee name
      let callee = null;
      if (n.callee.type === "Identifier") callee = n.callee.name;
      else if (n.callee.type === "MemberExpression" && n.callee.property.type === "Identifier") callee = n.callee.property.name;
      if (callee) calls.add(callee);

      // endpoints in handler
      if (callee && (callee === "fetch" || callee === "apiJSON" || callee === "api")) {
        const a0 = n.arguments?.[0];
        const v = argToStrOrTemplate(a0);
        if (typeof v === "string") {
          if (v.startsWith("/") || v.includes("/meatze")) endpoints.add(v);
          else if (v.includes("/meatze") || v.includes("/v5") || v.includes("/admin")) endpointsTemplates.add(v);
        }
      }

      // selector hints from event delegation patterns
      // e.target.matches("...") / e.target.closest("...")
      if (n.callee?.type === "MemberExpression" && n.callee.property?.type === "Identifier") {
        const m = n.callee.property.name;
        if (m === "matches" || m === "closest") {
          const a0 = n.arguments?.[0];
          if (a0?.type === "Literal" && typeof a0.value === "string") {
            selectorHints.add(a0.value);
          }
        }
      }
    }
  });

  return {
    calls: [...calls],
    endpoints: [...endpoints],
    endpointsTemplates: [...endpointsTemplates],
    selectorHints: [...selectorHints],
  };
}

// Helper: detect pattern
// document.querySelectorAll("SEL").forEach(el => el.addEventListener("click", ...))
function detectQsaForEachPattern(node) {
  // returns { selector, eventName, handlerNode, line } or null
  if (node.type !== "CallExpression") return null;
  if (node.callee?.type !== "MemberExpression") return null;
  if (node.callee.property?.type !== "Identifier" || node.callee.property.name !== "forEach") return null;

  const qsaCall = node.callee.object;
  if (!qsaCall || qsaCall.type !== "CallExpression") return null;
  if (qsaCall.callee?.type !== "MemberExpression") return null;

  const obj = qsaCall.callee.object;
  const prop = qsaCall.callee.property;
  if (!(obj?.type === "Identifier" && obj.name === "document")) return null;
  if (!(prop?.type === "Identifier" && prop.name === "querySelectorAll")) return null;

  const selArg = qsaCall.arguments?.[0];
  if (!(selArg?.type === "Literal" && typeof selArg.value === "string")) return null;

  const cb = node.arguments?.[0];
  if (!cb || (cb.type !== "ArrowFunctionExpression" && cb.type !== "FunctionExpression")) return null;

  // inside callback body search first-level addEventListener on its param
  const body = cb.body?.type === "BlockStatement" ? cb.body.body : [];
  for (const st of body) {
    if (st.type !== "ExpressionStatement") continue;
    const expr = st.expression;
    if (expr?.type !== "CallExpression") continue;
    if (expr.callee?.type !== "MemberExpression") continue;
    if (expr.callee.property?.type !== "Identifier" || expr.callee.property.name !== "addEventListener") continue;

    const evArg = expr.arguments?.[0];
    const handler = expr.arguments?.[1];
    const eventName = (evArg?.type === "Literal" && typeof evArg.value === "string") ? evArg.value : null;

    return {
      selector: selArg.value,
      eventName,
      handlerNode: handler,
      line: expr.loc?.start?.line ?? node.loc?.start?.line ?? null,
    };
  }

  return null;
}

// Helper: detect event array pattern:
// ['change','input'].forEach(ev => el.addEventListener(ev, handler))
function detectEventArrayPattern(node) {
  // returns { eventNames:[], selector:null, handlerNode, line } or null
  if (node.type !== "CallExpression") return null;
  if (node.callee?.type !== "MemberExpression") return null;
  if (node.callee.property?.type !== "Identifier" || node.callee.property.name !== "forEach") return null;

  const arr = node.callee.object;
  if (!arr || arr.type !== "ArrayExpression") return null;

  const eventNames = [];
  for (const el of arr.elements || []) {
    if (el?.type === "Literal" && typeof el.value === "string") eventNames.push(el.value);
    else return null; // not strict literal array
  }

  const cb = node.arguments?.[0];
  if (!cb || (cb.type !== "ArrowFunctionExpression" && cb.type !== "FunctionExpression")) return null;

  // callback param name (ev)
  const evParam = cb.params?.[0]?.type === "Identifier" ? cb.params[0].name : null;

  // look for addEventListener(evParam, handler) inside cb
  const bodyNodes = cb.body?.type === "BlockStatement" ? cb.body.body : [];
  for (const st of bodyNodes) {
    if (st.type !== "ExpressionStatement") continue;
    const expr = st.expression;
    if (expr?.type !== "CallExpression") continue;
    if (expr.callee?.type !== "MemberExpression") continue;
    if (expr.callee.property?.type !== "Identifier" || expr.callee.property.name !== "addEventListener") continue;

    const evArg = expr.arguments?.[0];
    const handler = expr.arguments?.[1];
    if (!evParam) continue;
    if (evArg?.type === "Identifier" && evArg.name === evParam) {
      return {
        eventNames,
        handlerNode: handler,
        line: expr.loc?.start?.line ?? node.loc?.start?.line ?? null,
      };
    }
  }

  return null;
}

const actions = [];

// 1) direct: something.addEventListener("click", handler)
walk.simple(ast, {
  CallExpression(node) {
    // A) querySelectorAll(...).forEach(el=> el.addEventListener(...))
    const qsa = detectQsaForEachPattern(node);
    if (qsa) {
      let handlerName = null;
      let hints = { calls: [], endpoints: [], endpointsTemplates: [], selectorHints: [] };

      if (qsa.handlerNode?.type === "Identifier") handlerName = qsa.handlerNode.name;
      if (qsa.handlerNode && (qsa.handlerNode.type === "FunctionExpression" || qsa.handlerNode.type === "ArrowFunctionExpression")) {
        const bodyNode = qsa.handlerNode.body?.type === "BlockStatement" ? qsa.handlerNode.body : qsa.handlerNode;
        hints = collectHandlerHints(bodyNode);
      }

      actions.push({
        selector: qsa.selector,
        event: qsa.eventName || "(unknown event)",
        line: qsa.line,
        handlerName,
        calls: hints.calls,
        endpoints: hints.endpoints,
        endpointsTemplates: hints.endpointsTemplates,
        selectorHints: hints.selectorHints,
        source: "qsa.forEach.addEventListener"
      });
      return;
    }

    // B) array of events: ['change','input'].forEach(ev => el.addEventListener(ev, handler))
    const evArr = detectEventArrayPattern(node);
    if (evArr) {
      // selector unknown here (we don't know which element without more context)
      let handlerName = null;
      let hints = { calls: [], endpoints: [], endpointsTemplates: [], selectorHints: [] };

      if (evArr.handlerNode?.type === "Identifier") handlerName = evArr.handlerNode.name;
      if (evArr.handlerNode && (evArr.handlerNode.type === "FunctionExpression" || evArr.handlerNode.type === "ArrowFunctionExpression")) {
        const bodyNode = evArr.handlerNode.body?.type === "BlockStatement" ? evArr.handlerNode.body : evArr.handlerNode;
        hints = collectHandlerHints(bodyNode);
      }

      actions.push({
        selector: null,
        event: `[${evArr.eventNames.join(", ")}]`,
        line: evArr.line,
        handlerName,
        calls: hints.calls,
        endpoints: hints.endpoints,
        endpointsTemplates: hints.endpointsTemplates,
        selectorHints: hints.selectorHints,
        source: "eventArray.forEach.addEventListener"
      });
      return;
    }

    // C) direct addEventListener
    if (node.callee?.type !== "MemberExpression") return;
    if (node.callee.property?.type !== "Identifier") return;
    if (node.callee.property.name !== "addEventListener") return;

    const evArg = node.arguments?.[0];
    const handler = node.arguments?.[1];

    const eventName = (evArg?.type === "Literal" && typeof evArg.value === "string") ? evArg.value : null;

    // Try to guess selector from callee.object
    let selector = selFromNode(node.callee.object);

	// if target is Identifier: btnNext.addEventListener(...)
	if (!selector && node.callee.object?.type === "Identifier") {
	  const mapped = idToSelector.get(node.callee.object.name);
	  if (mapped) selector = mapped;
	}


    // Handler name if Identifier
    const handlerName = handler?.type === "Identifier" ? handler.name : null;

    // If handler is inline function/arrow, analyze inside
    let hints = { calls: [], endpoints: [], endpointsTemplates: [], selectorHints: [] };
    if (handler && (handler.type === "FunctionExpression" || handler.type === "ArrowFunctionExpression")) {
      const bodyNode = handler.body?.type === "BlockStatement" ? handler.body : handler;
      hints = collectHandlerHints(bodyNode);
    }

    actions.push({
      selector,
      event: eventName || "(unknown event)",
      line: node.loc?.start?.line ?? null,
      handlerName,
      calls: hints.calls,
      endpoints: hints.endpoints,
      endpointsTemplates: hints.endpointsTemplates,
      selectorHints: hints.selectorHints,
      source: "direct.addEventListener"
    });
  }
});
walk.simple(ast, {
  VariableDeclarator(node) {
    learnSelectorAssignment(node);
  }
});

console.log(JSON.stringify({ actions }, null, 2));
