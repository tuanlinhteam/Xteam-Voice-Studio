// In-memory / Global store for demo, easily persisted with KV or JSON
let globalLicenses = global._xteamLicenses || {
  "XTM-889B-AD92-6AC8": {
    customer_name: "Admin Xteam (Mẫu)",
    hwid: "XTM-889B-AD92-6AC8",
    created_at: "2026-09-28",
    expires_at: "2027-09-28",
    plan: "Vĩnh viễn / VIP",
    active: true
  }
};
global._xteamLicenses = globalLicenses;

module.exports = async (req, res) => {
  // Enable CORS
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  let hwid = "";
  if (req.method === "POST") {
    hwid = (req.body && req.body.hwid) || "";
  } else {
    hwid = req.query.hwid || "";
  }

  hwid = (hwid || "").trim().toUpperCase();

  if (!hwid) {
    return res.status(400).json({ active: false, message: "Thiếu mã máy (HWID)" });
  }

  const lic = global._xteamLicenses[hwid];

  if (!lic || !lic.active) {
    return res.status(200).json({
      active: false,
      hwid: hwid,
      customer_name: "Chưa kích hoạt",
      message: "Mã máy chưa được kích hoạt bản quyền trên hệ thống."
    });
  }

  // Calculate expiration date
  const now = new Date();
  const expireDate = new Date(lic.expires_at);
  const diffTime = expireDate - now;
  const daysLeft = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

  if (daysLeft < 0) {
    return res.status(200).json({
      active: false,
      hwid: hwid,
      customer_name: lic.customer_name,
      expires_at: lic.expires_at,
      days_left: 0,
      message: "Bản quyền đã hết hạn sử dụng. Vui lòng liên hệ Admin để gia hạn."
    });
  }

  return res.status(200).json({
    active: true,
    hwid: hwid,
    customer_name: lic.customer_name,
    expires_at: lic.expires_at,
    days_left: daysLeft,
    plan: lic.plan || "VIP",
    message: "Bản quyền hợp lệ và đang hoạt động."
  });
};
