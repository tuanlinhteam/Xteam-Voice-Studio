const http = require('http');
const fs = require('fs');
const path = require('path');
const checkLicense = require('./api/check-license');
const adminLicenses = require('./api/admin/licenses');

const PORT = 3000;

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  
  // Body parser helper
  let body = {};
  if (req.method === 'POST' || req.method === 'DELETE') {
    const buffers = [];
    for await (const chunk of req) {
      buffers.push(chunk);
    }
    const raw = Buffer.concat(buffers).toString();
    try {
      body = JSON.parse(raw);
    } catch (e) {}
  }
  req.body = body;
  req.query = Object.fromEntries(url.searchParams);

  if (url.pathname === '/api/check-license') {
    return checkLicense(req, res);
  }

  if (url.pathname === '/api/admin/licenses') {
    return adminLicenses(req, res);
  }

  // Serve static files
  let filePath = path.join(__dirname, 'public', url.pathname === '/' ? 'index.html' : url.pathname);
  if (fs.existsSync(filePath)) {
    const ext = path.extname(filePath);
    const contentType = ext === '.html' ? 'text/html' : ext === '.js' ? 'text/javascript' : ext === '.css' ? 'text/css' : 'text/plain';
    res.writeHead(200, { 'Content-Type': contentType });
    return fs.createReadStream(filePath).pipe(res);
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`[+] Vercel License Server dang chay tai: http://localhost:${PORT}`);
  console.log(`[+] Admin Dashboard: http://localhost:${PORT}`);
});
