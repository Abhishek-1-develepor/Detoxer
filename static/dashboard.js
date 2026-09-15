/* ============================================================
   Detoxer Dashboard — Frontend Logic
   ============================================================ */

let allProducts = [];
let editingProductId = null;

/* ============================================================
   DOM REFS
   ============================================================ */
const productTableBody = document.getElementById("productTableBody");
const searchInput      = document.getElementById("searchInput");
const totalProductsEl  = document.getElementById("totalProducts");
const lowStockCountEl  = document.getElementById("lowStockCount");
const averagePriceEl   = document.getElementById("averagePrice");
const addProductBtn    = document.getElementById("addProductBtn");
const exportBtn        = document.getElementById("exportBtn");
const categoryListEl   = document.getElementById("categoryList");

const modal            = document.getElementById("productModal");
const modalTitle       = document.getElementById("modalTitle");
const productForm      = document.getElementById("productForm");
const closeModalBtn    = document.getElementById("closeModalBtn");
const cancelBtn        = document.getElementById("cancelBtn");
const saveBtn          = document.getElementById("saveBtn");

/* ============================================================
   HELPERS
   ============================================================ */
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatPrice(v) {
  return `$${Number(v || 0).toFixed(0)}`;
}

function fallbackImage(name) {
  const text = encodeURIComponent((name || "Item").slice(0, 10));
  return `https://via.placeholder.com/100x100/7c3aed/ffffff?text=${text}`;
}

function statusClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "in stock") return "in-stock";
  if (s === "low stock") return "low";
  return "critical";
}

function statusBadge(status) {
  return `<span class="status ${statusClass(status)}">${escapeHtml(status)}</span>`;
}

/* ============================================================
   RENDER: STATS
   ============================================================ */
function renderStats() {
  const total    = allProducts.length;
  const lowStock = allProducts.filter(p => Number(p.stock) < 20).length;
  const avg      = total
    ? allProducts.reduce((s, p) => s + Number(p.price || 0), 0) / total
    : 0;

  if (totalProductsEl) totalProductsEl.textContent = total;
  if (lowStockCountEl) lowStockCountEl.textContent = lowStock;
  if (averagePriceEl)  averagePriceEl.textContent  = formatPrice(avg);
}

/* ============================================================
   RENDER: CATEGORIES
   ============================================================ */
function renderCategories() {
  if (!categoryListEl) return;

  const counts = {};
  allProducts.forEach(p => {
    const cat = p.category || "General";
    counts[cat] = (counts[cat] || 0) + 1;
  });

  const total  = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  const colors = ["#8b5cf6", "#2563eb", "#f59e0b", "#22c55e"];
  const sorted = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);

  if (!sorted.length) {
    categoryListEl.innerHTML = `
      <div class="category-item">
        <div class="label"><span class="dot" style="background:#8b5cf6"></span><span>No categories yet</span></div>
        <strong>0%</strong>
      </div>`;
    return;
  }

  categoryListEl.innerHTML = sorted
    .map(([name, count], i) => {
      const pct = Math.round((count / total) * 100);
      return `
        <div class="category-item">
          <div class="label">
            <span class="dot" style="background:${colors[i % colors.length]}"></span>
            <span>${escapeHtml(name)}</span>
          </div>
          <strong>${pct}%</strong>
        </div>`;
    })
    .join("");
}

/* ============================================================
   RENDER: PRODUCT TABLE
   ============================================================ */
function renderTable(filterText = "") {
  if (!productTableBody) return;

  const keyword = filterText.trim().toLowerCase();
  const list = keyword
    ? allProducts.filter(p =>
        [p.name, p.category, p.status].join(" ").toLowerCase().includes(keyword)
      )
    : allProducts;

  if (!list.length) {
    productTableBody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align:center;padding:40px;color:#667085;">
          No products found.
        </td>
      </tr>`;
    return;
  }

  productTableBody.innerHTML = list
    .map(p => {
      const img = p.image_url && p.image_url.trim()
        ? p.image_url
        : fallbackImage(p.name);

      return `
        <tr data-id="${p.id}">
          <td>
            <div class="product-cell">
              <div
                class="product-thumb"
                style="background-image:url('${escapeHtml(img)}');"
                onerror="this.style.backgroundImage='url(${fallbackImage(p.name)})'"
              ></div>
              <div>
                <strong>${escapeHtml(p.name)}</strong>
                <small>${escapeHtml(p.category)}</small>
              </div>
            </div>
          </td>
          <td>${escapeHtml(p.category)}</td>
          <td>${formatPrice(p.price)}</td>
          <td>${escapeHtml(p.stock)}</td>
          <td>${statusBadge(p.status)}</td>
          <td>
            <div class="row-actions">
              <button class="mini-btn edit"   type="button" data-id="${p.id}">Edit</button>
              <button class="mini-btn review" data-id="${p.id}" type="button">Reviews</button>
              <button class="mini-btn delete" type="button" data-id="${p.id}">Delete</button>
            </div>
          </td>
        </tr>`;
    })
    .join("");
}

/* ============================================================
   RENDER: ALL
   ============================================================ */
function renderAll() {
  renderStats();
  renderCategories();
  renderTable(searchInput ? searchInput.value : "");
}

/* ============================================================
   API: LOAD
   ============================================================ */
async function loadProducts() {
  try {
    const res = await fetch("/api/products");
    if (!res.ok) throw new Error("Failed to load");
    const data = await res.json();
    allProducts = Array.isArray(data) ? data : [];
    renderAll();
  } catch (err) {
    console.error(err);
    if (productTableBody) {
      productTableBody.innerHTML = `
        <tr><td colspan="6" style="text-align:center;padding:40px;color:#ef4444;">
          Failed to load products. Check the console / server.
        </td></tr>`;
    }
  }
}

/* ============================================================
   MODAL
   ============================================================ */
function openModal(product = null) {
  if (!modal || !productForm) return;

  productForm.reset();
  editingProductId = null;

  if (product) {
    modalTitle.textContent = "Edit Product";
    saveBtn.textContent    = "Update Product";
    editingProductId       = product.id;

    productForm.product_name.value        = product.name        || "";
    productForm.category.value            = product.category    || "";
    productForm.price.value               = product.price       ?? 0;
    productForm.stock_quantity.value      = product.stock       ?? 0;
    productForm.status.value              = product.status      || "In Stock";
    productForm.image_url.value           = product.image_url   || "";
    productForm.product_description.value = product.description || "";
    productForm.review.value              = product.review      || "";
  } else {
    modalTitle.textContent = "Add Product";
    saveBtn.textContent    = "Save Product";
  }

  modal.classList.remove("hidden");
}

function closeModal() {
  if (modal) modal.classList.add("hidden");
  editingProductId = null;
}

/* ============================================================
   SUBMIT FORM (CREATE / UPDATE)
   ============================================================ */
async function handleSubmit(e) {
  e.preventDefault();

  const fd = new FormData(productForm);

  const payload = {
    product_name:        String(fd.get("product_name") || "").trim(),
    category:            String(fd.get("category") || "General").trim(),
    product_description: String(fd.get("product_description") || "").trim(),
    price:               Number(fd.get("price")) || 0,
    stock_quantity:      Number(fd.get("stock_quantity")) || 0,
    status:              String(fd.get("status") || "In Stock").trim(),
    image_url:           String(fd.get("image_url") || "").trim(),
    review:              String(fd.get("review") || "").trim(),
  };

  if (!payload.product_name || !payload.category) {
    alert("Product name and category are required.");
    return;
  }

  saveBtn.disabled    = true;
  saveBtn.textContent = editingProductId ? "Updating…" : "Saving…";

  try {
    const url    = editingProductId ? `/api/products/${editingProductId}` : "/api/products";
    const method = editingProductId ? "PUT" : "POST";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.message || "Failed to save");
    }

    closeModal();
    await loadProducts();
  } catch (err) {
    console.error(err);
    alert(err.message || "Something went wrong");
  } finally {
    saveBtn.disabled    = false;
    saveBtn.textContent = editingProductId ? "Update Product" : "Save Product";
  }
}

/* ============================================================
   DELETE
   ============================================================ */
async function deleteProduct(id) {
  const p    = allProducts.find(x => x.id === id);
  const name = p ? p.name : "this product";

  if (!confirm(`Delete "${name}"?`)) return;

  try {
    const res  = await fetch(`/api/products/${id}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || "Delete failed");
    await loadProducts();
  } catch (err) {
    console.error(err);
    alert(err.message || "Delete failed");
  }
}

/* ============================================================
   EXPORT CSV
   ============================================================ */
function exportCSV() {
  if (!allProducts.length) {
    alert("No products to export.");
    return;
  }

  const headers = ["ID", "Name", "Category", "Price", "Stock", "Status", "Image URL"];
  const rows = allProducts.map(p => [
    p.id, p.name, p.category, p.price, p.stock, p.status, p.image_url,
  ]);

  const csv = [headers, ...rows]
    .map(r => r.map(c => `"${String(c ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `products_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/* ============================================================
   EVENT BINDING
   ============================================================ */
function bindEvents() {
  if (addProductBtn) addProductBtn.addEventListener("click", () => openModal());
  if (closeModalBtn) closeModalBtn.addEventListener("click", closeModal);
  if (cancelBtn)     cancelBtn.addEventListener("click", closeModal);

  if (modal) {
    modal.addEventListener("click", e => {
      if (e.target === modal) closeModal();
    });
  }

  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && modal && !modal.classList.contains("hidden")) {
      closeModal();
    }
  });

  if (productForm) productForm.addEventListener("submit", handleSubmit);

  if (searchInput) {
    searchInput.addEventListener("input", e => renderTable(e.target.value));
  }

  if (productTableBody) {
  productTableBody.addEventListener("click", (e) => {
    const reviewBtn = e.target.closest(".mini-btn.review");
    const editBtn   = e.target.closest(".mini-btn.edit");
    const deleteBtn = e.target.closest(".mini-btn.delete");

    if (reviewBtn) {
      const id = Number(reviewBtn.dataset.id);
      window.location.href = `/admin/product/${id}/reviews`;
    }
    if (editBtn) {
      const id = Number(editBtn.dataset.id);
      const p = allProducts.find(x => x.id === id);
      if (p) openModal(p);
    }
    if (deleteBtn) {
      deleteProduct(Number(deleteBtn.dataset.id));
    }
  });
}
  if (exportBtn) exportBtn.addEventListener("click", exportCSV);
}

/* ============================================================
   INIT
   ============================================================ */
document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  loadProducts();
});