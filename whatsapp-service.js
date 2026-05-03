const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const path = require('path');

let client = null;
let _status = 'disconnected'; // disconnected | qr | connecting | ready
let _qrCode = null; // base64 PNG data URL
let _initPromise = null;

function getStatus() {
  return { status: _status, qrCode: _qrCode };
}

async function initialize() {
  if (_initPromise) return _initPromise;

  _initPromise = _createClient();
  return _initPromise;
}

async function _createClient() {
  _status = 'connecting';
  _qrCode = null;

  client = new Client({
    authStrategy: new LocalAuth({
      dataPath: path.join(__dirname, '.wwebjs_auth')
    }),
    puppeteer: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu'
      ]
    }
  });

  client.on('qr', async (qr) => {
    _status = 'qr';
    _qrCode = await qrcode.toDataURL(qr);
    console.log('[WhatsApp] QR code generated — please scan');
  });

  client.on('loading_screen', (percent) => {
    _status = 'connecting';
    _qrCode = null;
    console.log(`[WhatsApp] Loading ${percent}%`);
  });

  client.on('authenticated', () => {
    _status = 'connecting';
    _qrCode = null;
    console.log('[WhatsApp] Authenticated');
  });

  client.on('ready', () => {
    _status = 'ready';
    _qrCode = null;
    console.log('[WhatsApp] Client ready');
  });

  client.on('auth_failure', (msg) => {
    _status = 'disconnected';
    _qrCode = null;
    _initPromise = null;
    client = null;
    console.error('[WhatsApp] Auth failure:', msg);
  });

  client.on('disconnected', (reason) => {
    _status = 'disconnected';
    _qrCode = null;
    _initPromise = null;
    client = null;
    console.log('[WhatsApp] Disconnected:', reason);
  });

  await client.initialize();
}

/**
 * Sends a WhatsApp message. Throws if client is not ready.
 * @param {string} phone - any format: +49..., 0049..., 0176..., 176...
 * @param {string} message
 */
async function sendMessage(phone, message) {
  if (!client || _status !== 'ready') {
    throw new Error('WhatsApp client not ready');
  }
  const chatId = formatPhone(phone) + '@c.us';
  await client.sendMessage(chatId, message);
}

/**
 * Normalises a phone number to international digits only (no + or spaces).
 * Assumes German numbers if only 10 digits starting with 0.
 */
function formatPhone(phone) {
  let n = phone.replace(/\D/g, '');

  if (n.startsWith('00')) n = n.slice(2);
  else if (n.startsWith('0')) n = '49' + n.slice(1);

  return n;
}

module.exports = { initialize, sendMessage, getStatus, formatPhone };
