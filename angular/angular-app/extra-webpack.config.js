const webpack = require('webpack')
const HtmlWebpackPlugin = require('html-webpack-plugin');
const keyPrefix = 'ANGULAR_';

const keys = Object.keys(process.env).filter((key) => key.startsWith(keyPrefix));
let env = {};
keys.forEach(key => env[key] = JSON.stringify(process.env[key]));
console.log('env=',env);
module.exports = {
  plugins: [
    new HtmlWebpackPlugin({ template: './src/index.html' }),
    new webpack.DefinePlugin({
      'ENV_VARS': env
    })
  ]
}
