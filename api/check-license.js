const FIREBASE_DB_URL = process.env.FIREBASE_DB_URL || "https://xteam-328bc-default-rtdb.firebaseio.com";

module.exports = async (req, res) => {
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

  try {
    // Truy vấn dữ liệu mã máy theo thời gian thực từ Firebase Realtime Database
    const fbRes = await fetch(`${FIREBASE_DB_URL}/licenses/${encodeURIComponent(hwid)}.json`);
    const lic = await fbRes.json();

    if (!lic || !lic.active) {
      return res.status(200).json({
        active: false,
        hwid: hwid,
        customer_name: "Chưa kích hoạt",
        message: "Mã máy chưa được kích hoạt bản quyền trên hệ thống Firebase."
      });
    }

    // Tính toán thời hạn
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
  } catch (err) {
    console.error("Firebase fetch error:", err);
    return res.status(500).json({
      active: false,
      hwid: hwid,
      message: "Lỗi kết nối Firebase Realtime Database."
    });
  }
};
