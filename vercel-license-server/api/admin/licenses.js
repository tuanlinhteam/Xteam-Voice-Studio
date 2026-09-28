const FIREBASE_DB_URL = process.env.FIREBASE_DB_URL || "https://xteam-328bc-default-rtdb.firebaseio.com";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin123";

module.exports = async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Admin-Key");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  const adminKey = req.headers["x-admin-key"] || (req.query && req.query.key) || (req.body && req.body.key);
  if (adminKey !== ADMIN_PASSWORD) {
    return res.status(401).json({ success: false, message: "Mật khẩu Admin không chính xác!" });
  }

  // GET: Lấy danh sách tất cả khách hàng từ Firebase
  if (req.method === "GET") {
    try {
      const fbRes = await fetch(`${FIREBASE_DB_URL}/licenses.json`);
      const data = await fbRes.json();
      
      if (!data) {
        return res.status(200).json({ success: true, licenses: [] });
      }

      const list = Object.values(data).map(item => {
        const now = new Date();
        const expireDate = new Date(item.expires_at);
        const daysLeft = Math.ceil((expireDate - now) / (1000 * 60 * 60 * 24));
        return {
          ...item,
          days_left: Math.max(0, daysLeft),
          is_expired: daysLeft < 0
        };
      });

      // Sắp xếp khách hàng mới lên đầu
      list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

      return res.status(200).json({ success: true, licenses: list });
    } catch (err) {
      return res.status(500).json({ success: false, message: "Lỗi đọc dữ liệu từ Firebase: " + err.message });
    }
  }

  // POST: Kích hoạt mới hoặc Gia hạn khách hàng trên Firebase
  if (req.method === "POST") {
    const { customer_name, hwid, days, expires_at, plan, active } = req.body;
    
    if (!hwid || !customer_name) {
      return res.status(400).json({ success: false, message: "Vui lòng nhập đầy đủ Mã máy và Tên khách hàng!" });
    }

    const cleanHwid = hwid.trim().toUpperCase();
    let finalExpire = expires_at;

    if (!finalExpire && days) {
      const d = new Date();
      d.setDate(d.getDate() + parseInt(days));
      finalExpire = d.toISOString().split("T")[0];
    } else if (!finalExpire) {
      const d = new Date();
      d.setDate(d.getDate() + 30);
      finalExpire = d.toISOString().split("T")[0];
    }

    const newLic = {
      customer_name: customer_name.trim(),
      hwid: cleanHwid,
      created_at: new Date().toISOString().split("T")[0],
      expires_at: finalExpire,
      plan: plan || "Bản quyền VIP",
      active: active !== undefined ? active : true,
      updated_at: new Date().toISOString()
    };

    try {
      // Lưu realtime vào Firebase
      await fetch(`${FIREBASE_DB_URL}/licenses/${encodeURIComponent(cleanHwid)}.json`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newLic)
      });

      return res.status(200).json({
        success: true,
        message: `Đã kích hoạt realtime cho khách hàng ${customer_name}!`,
        license: newLic
      });
    } catch (err) {
      return res.status(500).json({ success: false, message: "Lỗi lưu vào Firebase: " + err.message });
    }
  }

  // DELETE: Xóa hoặc khóa khách hàng trên Firebase
  if (req.method === "DELETE") {
    const hwid = (req.query.hwid || (req.body && req.body.hwid) || "").trim().toUpperCase();
    if (!hwid) {
      return res.status(400).json({ success: false, message: "Thiếu mã máy cần xóa." });
    }

    try {
      await fetch(`${FIREBASE_DB_URL}/licenses/${encodeURIComponent(hwid)}.json`, {
        method: "DELETE"
      });
      return res.status(200).json({ success: true, message: `Đã xóa bản quyền mã máy ${hwid} khỏi Firebase` });
    } catch (err) {
      return res.status(500).json({ success: false, message: "Lỗi xóa trên Firebase: " + err.message });
    }
  }

  return res.status(405).json({ message: "Method Not Allowed" });
};
