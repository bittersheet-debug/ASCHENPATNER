/**
 * ASCHEN EVENT ORGANIZER - Admin Authentication Middleware
 */

const jwt = require('jsonwebtoken');
const { JWT_SECRET } = require('../../config');
const db = require('../database/db');

function generateToken(admin) {
  return jwt.sign(
    {
      id: admin.id,
      username: admin.username,
      name: admin.name,
      role: admin.role
    },
    JWT_SECRET,
    { expiresIn: '7d' }
  );
}

function authMiddleware(req, res, next) {
  const token = req.cookies.admin_token || (req.headers.authorization && req.headers.authorization.split(' ')[1]);

  if (!token) {
    return res.status(401).json({ error: 'Akses ditolak. Silakan login terlebih dahulu.' });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.admin = decoded;
    next();
  } catch (err) {
    res.clearCookie('admin_token');
    return res.status(401).json({ error: 'Sesi telah kedaluwarsa. Silakan login kembali.' });
  }
}

module.exports = { generateToken, authMiddleware };
