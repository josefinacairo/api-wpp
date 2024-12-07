module.exports = {
    apps: [
      {
        name: 'app',
        script: './app.ts',
        interpreter: './node_modules/.bin/ts-node',
        env: {
          NODE_ENV: 'production',
          PORT: 3002
        }
      }
    ]
  };
  