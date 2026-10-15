const { compile } = require('markdown-include');

compile({
  srcDir: '.',
  destDir: '.',
  files: ['README.src.md'],
});
