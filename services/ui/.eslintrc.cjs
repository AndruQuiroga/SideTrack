const path = require('path');

// Ensure ESLint resolves plugins from this package's node_modules.
module.paths.push(path.resolve(__dirname, 'node_modules'));

module.exports = require('../../.eslintrc.cjs');
