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

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "xteam2026";

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

  // GET: List all licenses
  if (req.method === "GET") {
    const list = Object.values(global._xteamLicenses).map(item => {
      const now = new Date();
      const expireDate = new Date(item.expires_at);
      const daysLeft = Math.ceil((expireDate - now) / (1000 * 60 * 60 * 24));
      return {
        ...item,
        days_left: Math.max(0, daysLeft),
        is_expired: daysLeft < 0
      };
    });
    return res.status(200).json({ success: true, licenses: list });
  }

  // POST: Add or Update License
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
      // Default 30 days
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
      active: active !== undefined ? active : true
    };

    global._xteamLicenses[cleanHwid] = newLic;
    return res.status(200).json({ success: true, message: `Đã kích hoạt thành công cho khách hàng ${customer_name}!`, license: newLic });
  }

  // DELETE: Delete a License
  if (req.method === "DELETE") {
    const hwid = (req.query.hwid || (req.body && req.body.hwid) || "").trim().toUpperCase();
    if (global._xteamLicenses[hwid]) {
      delete global._xteamLicenses[hwid];
      return res.status(200).json({ success: true, message: `Đã xóa bản quyền mã máy ${hwid}` });
    }
    return res.status(404).json({ success: false, message: "Không tìm thấy mã máy này." });
  }

  return res.status(405).json({ message: "Method Not Allowed" });
};
