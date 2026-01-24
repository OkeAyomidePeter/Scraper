const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
} = require("@whiskeysockets/baileys");
const qrcode = require("qrcode-terminal");
const express = require("express");
const bodyParser = require("body-parser");
const pino = require("pino");
const path = require("path");

const app = express();
app.use(bodyParser.json());

const port = 3000;
let sock;
let isReady = false;

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState("baileys_auth_info");

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger: pino({ level: "silent" }),
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("QR RECEIVED. Scan this QR code with your WhatsApp app:");
      qrcode.generate(qr, { small: true });
    }

    if (connection === "close") {
      const shouldReconnect =
        lastDisconnect.error?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log("Connection closed. Reconnecting...", shouldReconnect);
      if (shouldReconnect) {
        connectToWhatsApp();
      } else {
        isReady = false;
      }
    } else if (connection === "open") {
      console.log("WhatsApp Client is ready! (Baileys)");
      isReady = true;
    }
  });
}

// API Endpoints
app.get("/status", (req, res) => {
  res.json({ ready: isReady });
});

app.post("/send", async (req, res) => {
  const { phone, message } = req.body;

  if (!isReady) {
    return res.status(503).json({ error: "WhatsApp client is not ready" });
  }

  if (!phone || !message) {
    return res.status(400).json({ error: "Phone and message are required" });
  }

  try {
    // Baileys format: <number>@s.whatsapp.net
    let formattedPhone = phone.replace(/\D/g, "");
    if (formattedPhone.startsWith("0")) {
      formattedPhone = "234" + formattedPhone.slice(1);
    }
    const id = `${formattedPhone}@s.whatsapp.net`;

    console.log(`Sending message to ${id}...`);
    await sock.sendMessage(id, { text: message });

    console.log(`Message successfully sent to ${phone}`);
    res.json({ success: true });
  } catch (error) {
    console.error("Error sending message:", error);
    res
      .status(500)
      .json({ error: "Failed to send message", details: error.message });
  }
});

app.listen(port, () => {
  console.log(
    `WhatsApp service (Baileys) listening at http://localhost:${port}`,
  );
  connectToWhatsApp();
});
