import fs from 'fs';
import esprima from 'esprima';
import estraverse from 'estraverse';

const filePath = process.argv[2];
if (!filePath) {
  console.error('Usage: node js_introspect.mjs <file.js>');
  process.exit(1);
}

const code = fs.readFileSync(filePath, 'utf8');
const ast = esprima.parseScript(code, { loc: true });

const result = {
  file: filePath,
  functions: [],
  calls: [],
  domSelectors: [],
  events: [],
  globals: []
};

const domSelectorsSet = new Set();
const eventsSet = new Set();
const globalsSet = new Set();

// Простое определение "глобалов": идентификаторы на верхнем уровне
if (ast.body) {
  for (const node of ast.body) {
    if (node.type === 'VariableDeclaration') {
      for (const d of node.declarations) {
        if (d.id && d.id.name) {
          globalsSet.add(d.id.name);
        }
      }
    }
    if (node.type === 'FunctionDeclaration' && node.id && node.id.name) {
      globalsSet.add(node.id.name);
    }
  }
}

estraverse.traverse(ast, {
  enter(node, parent) {
    // Функции: function foo() {}, const foo = () => {}, const foo = function() {}
    if (node.type === 'FunctionDeclaration') {
      result.functions.push({
        name: node.id ? node.id.name : null,
        type: 'function',
        params: node.params.map(p => p.name || null),
        loc: node.loc
      });
    }

    if (node.type === 'VariableDeclarator' &&
        node.id &&
        node.init &&
        (node.init.type === 'ArrowFunctionExpression' || node.init.type === 'FunctionExpression')
    ) {
      result.functions.push({
        name: node.id.name,
        type: node.init.type === 'ArrowFunctionExpression' ? 'arrow' : 'function_expr',
        params: node.init.params.map(p => p.name || null),
        loc: node.loc
      });
    }

    // Вызовы: fetch(...), apiJSON(...), addEventListener(...)
    if (node.type === 'CallExpression') {
      let calleeName = null;

      if (node.callee.type === 'Identifier') {
        calleeName = node.callee.name;
      } else if (node.callee.type === 'MemberExpression') {
        if (node.callee.property.type === 'Identifier') {
          calleeName = node.callee.property.name;
        }
      }

      const argsStrings = node.arguments.map(a => {
        if (a.type === 'Literal') return String(a.value);
        if (a.type === 'TemplateLiteral') {
          const quasis = a.quasis.map(q => q.value.raw).join('${...}');
          return '`' + quasis + '`';
        }
        return a.type;
      });

      result.calls.push({
        callee: calleeName,
        args: argsStrings,
        loc: node.loc
      });

      // DOM: document.getElementById / querySelector / querySelectorAll
      if (node.callee.type === 'MemberExpression') {
        const obj = node.callee.object;
        const prop = node.callee.property;
        if (obj.type === 'Identifier' && obj.name === 'document' && prop.type === 'Identifier') {
          const method = prop.name;
          if (['getElementById', 'querySelector', 'querySelectorAll'].includes(method)) {
            if (node.arguments.length > 0 && node.arguments[0].type === 'Literal') {
              const sel = String(node.arguments[0].value);
              domSelectorsSet.add(sel);
            }
          }
        }
      }

      // Слушатели событий: element.addEventListener('click', handler)
      if (node.callee.type === 'MemberExpression') {
        const prop = node.callee.property;
        if (prop.type === 'Identifier' && prop.name === 'addEventListener') {
          const eventArg = node.arguments[0];
          let evName = null;
          if (eventArg && eventArg.type === 'Literal') {
            evName = String(eventArg.value);
          }
          const locInfo = node.loc;
          if (evName) {
            eventsSet.add(`${evName} @ line ${locInfo.start.line}`);
          }
        }
      }
    }
  }
});

result.domSelectors = Array.from(domSelectorsSet);
result.events = Array.from(eventsSet);
result.globals = Array.from(globalsSet);

console.log(JSON.stringify(result, null, 2));
