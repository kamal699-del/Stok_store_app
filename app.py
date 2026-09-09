import streamlit as st
import pandas as pd
from supabase import create_client
import io

# --- KONEKSI SUPABASE ---
SUPABASE_URL = "https://fkfrgxplzqfgmgkzyqac.supabase.co"
SUPABASE_KEY = "sb_publishable_66pIXoRT35bWJ0sQwB0ftQ_wnSG5vUj"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Aplikasi Stok Store", layout="wide")
st.title("📦 Sistem Manajemen Stok Multi-Cabang")

# --- SIDEBAR MENU ---
menu = st.sidebar.selectbox("Pilih Menu Utama", [
    "Dashboard Stok", 
    "0. Master Data (Store & Produk)",
    "1. Stok Masuk", 
    "2. Mutasi Gudang", 
    "3. Stock Opname (SO)", 
    "4. Upload POS Kasir", 
    "5. Rekap Laporan"
])

# Ambil data master store & produk untuk dropdown
stores_res = supabase.table("stores").select("*").execute().data
products_res = supabase.table("products").select("*").execute().data

store_dict = {s['store_name']: s['id'] for s in stores_res} if stores_res else {}
prod_dict = {p['product_name']: p['id'] for p in products_res} if products_res else {}

# ==========================================
# 0. MASTER DATA (STORE & PRODUK)
# ==========================================
if menu == "0. Master Data (Store & Produk)":
    st.subheader("⚙️ Kelola Master Data Cabang Store & Produk")
    
    tab1, tab2 = st.tabs(["Tambah Store", "Tambah Produk"])
    
    with tab1:
        st.write("### Tambah Cabang Store Baru")
        with st.form("form_add_store"):
            new_store_name = st.text_input("Nama Store (Contoh: LC Rancamanyar)")
            new_store_loc = st.text_input("Lokasi / Alamat Store")
            submit_store = st.form_submit_button("Simpan Store")
            
            if submit_store and new_store_name:
                supabase.table("stores").insert({
                    "store_name": new_store_name,
                    "location": new_store_loc
                }).execute()
                st.success(f"Store '{new_store_name}' berhasil ditambahkan! Silakan refresh halaman.")
                
        st.write("### Daftar Store Saat Ini:")
        if stores_res:
            st.dataframe(pd.DataFrame(stores_res), use_container_width=True)
        else:
            st.info("Belum ada data store.")
            
    with tab2:
        st.write("### Tambah Produk Baru")
        with st.form("form_add_prod"):
            p_code = st.text_input("Kode Produk (SKU)")
            p_name = st.text_input("Nama Produk")
            p_price = st.number_input("Harga Jual", min_value=0, value=10000)
            p_cogs = st.number_input("HPP / COGS", min_value=0, value=5000)
            submit_prod = st.form_submit_button("Simpan Produk")
            
            if submit_prod and p_name:
                supabase.table("products").insert({
                    "product_code": p_code,
                    "product_name": p_name,
                    "price": p_price,
                    "cogs": p_cogs
                }).execute()
                st.success(f"Produk '{p_name}' berhasil ditambahkan!")
                
        st.write("### Daftar Produk Saat Ini:")
        if products_res:
            st.dataframe(pd.DataFrame(products_res), use_container_width=True)
        else:
            st.info("Belum ada data produk.")

# ==========================================
# 1. DASHBOARD STOK
# ==========================================
elif menu == "Dashboard Stok":
    st.subheader("📊 Posisi Stok Terkini per Store")
    if store_dict:
        selected_store_name = st.selectbox("Pilih Cabang Store", list(store_dict.keys()))
        store_id = store_dict[selected_store_name]
        
        inv_res = supabase.table("inventory_stock").select("*, products(product_code, product_name, price, cogs)").eq("store_id", store_id).execute().data
        
        if inv_res:
            df_display = []
            for item in inv_res:
                prod = item.get('products') or {}
                df_display.append({
                    "Kode Produk": prod.get('product_code', '-'),
                    "Nama Produk": prod.get('product_name', '-'),
                    "Stok Gudang": item.get('warehouse_stock'),
                    "Stok Operasional": item.get('operational_stock'),
                    "Stok Awal": item.get('initial_stock'),
                    "Stok Akhir": item.get('final_stock'),
                    "Harga": prod.get('price'),
                    "HPP (COGS)": prod.get('cogs')
                })
            st.dataframe(pd.DataFrame(df_display), use_container_width=True)
        else:
            st.info("Belum ada data inventaris untuk store ini.")
    else:
        st.warning("Belum ada store terdaftar. Silakan tambahkan store melalui menu '0. Master Data (Store & Produk)' di sidebar.")

# ==========================================
# 2. STOK MASUK
# ==========================================
elif menu == "1. Stok Masuk":
    st.subheader("📥 Input Stok Masuk Gudang")
    if store_dict and prod_dict:
        with st.form("form_stok_masuk"):
            s_store = st.selectbox("Store", list(store_dict.keys()))
            s_prod = st.selectbox("Produk", list(prod_dict.keys()))
            qty_in = st.number_input("Jumlah Masuk ke Gudang", min_value=1, value=10)
            notes = st.text_input("Catatan / Keterangan Supplier")
            submit = st.form_submit_button("Simpan Stok Masuk")
            
            if submit:
                st_id = store_dict[s_store]
                pr_id = prod_dict[s_prod]
                
                supabase.table("warehouse_in").insert({
                    "store_id": st_id, "product_id": pr_id, "quantity": qty_in, "notes": notes
                }).execute()
                
                inv = supabase.table("inventory_stock").select("*").eq("store_id", st_id).eq("product_id", pr_id).execute().data
                if inv:
                    old_wh = inv[0]['warehouse_stock']
                    new_wh = old_wh + qty_in
                    new_final = new_wh + inv[0]['operational_stock']
                    supabase.table("inventory_stock").update({
                        "warehouse_stock": new_wh, "final_stock": new_final
                    }).eq("store_id", st_id).eq("product_id", pr_id).execute()
                else:
                    supabase.table("inventory_stock").insert({
                        "store_id": st_id, "product_id": pr_id, "warehouse_stock": qty_in, "operational_stock": 0, "final_stock": qty_in
                    }).execute()
                    
                st.success("Stok masuk berhasil dicatat!")
    else:
        st.warning("Pastikan Anda sudah mengisi data Store dan Produk di menu Master Data.")

# ==========================================
# 3. MUTASI GUDANG
# ==========================================
elif menu == "2. Mutasi Gudang":
    st.subheader("🔄 Pengambilan Stok dari Gudang ke Operasional")
    if store_dict and prod_dict:
        with st.form("form_mutasi"):
            s_store = st.selectbox("Store", list(store_dict.keys()))
            s_prod = st.selectbox("Produk", list(prod_dict.keys()))
            qty_move = st.number_input("Jumlah yang Dipindahkan ke Operasional", min_value=1, value=5)
            submit_m = st.form_submit_button("Proses Mutasi")
            
            if submit_m:
                st_id = store_dict[s_store]
                pr_id = prod_dict[s_prod]
                
                inv = supabase.table("inventory_stock").select("*").eq("store_id", st_id).eq("product_id", pr_id).execute().data
                if inv:
                    current_wh = inv[0]['warehouse_stock']
                    if current_wh >= qty_move:
                        new_wh = current_wh - qty_move
                        new_op = inv[0]['operational_stock'] + qty_move
                        
                        supabase.table("stock_mutations").insert({
                            "store_id": st_id, "product_id": pr_id, "quantity_moved": qty_move
                        }).execute()
                        
                        supabase.table("inventory_stock").update({
                            "warehouse_stock": new_wh, "operational_stock": new_op
                        }).eq("store_id", st_id).eq("product_id", pr_id).execute()
                        
                        st.success("Mutasi berhasil!")
                    else:
                        st.error("Stok di gudang tidak mencukupi!")
    else:
        st.warning("Data store atau produk belum tersedia.")

# ==========================================
# 4. STOCK OPNAME (SO) OPERASIONAL
# ==========================================
elif menu == "3. Stock Opname (SO)":
    st.subheader("📋 Stock Opname (SO) Stok Operasional")
    if store_dict and prod_dict:
        with st.form("form_so"):
            s_store = st.selectbox("Store", list(store_dict.keys()))
            s_prod = st.selectbox("Produk", list(prod_dict.keys()))
            so_mode = st.radio("Pilihan SO", ["update", "add"], format_func=lambda x: "Update Stok (Timpa Fisik)" if x=="update" else "Tambah Stok (Koreksi)")
            counted = st.number_input("Jumlah Fisik Hasil Opname", min_value=0, value=10)
            submit_so = st.form_submit_button("Simpan Stock Opname")
            
            if submit_so:
                st_id = store_dict[s_store]
                pr_id = prod_dict[s_prod]
                
                inv = supabase.table("inventory_stock").select("*").eq("store_id", st_id).eq("product_id", pr_id).execute().data
                if inv:
                    old_final = inv[0]['final_stock']
                    old_init = inv[0]['initial_stock']
                    new_op = counted if so_mode == "update" else inv[0]['operational_stock'] + counted
                    new_final = inv[0]['warehouse_stock'] + new_op
                    usage = old_init - new_final 
                    
                    supabase.table("stock_opname").insert({
                        "store_id": st_id, "product_id": pr_id, "opname_type": so_mode,
                        "counted_qty": counted, "old_final_stock": old_final,
                        "new_final_stock": new_final, "usage_calculated": usage
                    }).execute()
                    
                    supabase.table("inventory_stock").update({
                        "operational_stock": new_op, "initial_stock": old_final, "final_stock": new_final
                    }).eq("store_id", st_id).eq("product_id", pr_id).execute()
                    
                    st.success(f"Stock Opname berhasil disimpan! Penggunaan terhitung: {usage}")
    else:
        st.warning("Data store atau produk belum tersedia.")

# ==========================================
# 5. UPLOAD POS KASIR (EXCEL)
# ==========================================
elif menu == "4. Upload POS Kasir":
    st.subheader("📁 Posting Penjualan dari File Excel POS")
    if store_dict:
        s_store = st.selectbox("Store Cabang", list(store_dict.keys()))
        shift = st.selectbox("Shift / Keterangan Waktu", ["Shift 1", "Shift 2", "Full Day"])
        uploaded_file = st.file_uploader("Unggah file Excel rekap POS", type=["xlsx", "xls"])
        
        if uploaded_file and st.button("Proses Upload Penjualan"):
            df_pos = pd.read_excel(uploaded_file)
            st.write("Preview Data Excel:", df_pos.head())
            st.success("File Excel berhasil dibaca!")
    else:
        st.warning("Tambahkan store terlebih dahulu.")

# ==========================================
# 6. REKAP LAPORAN
# ==========================================
elif menu == "5. Rekap Laporan":
    st.subheader("📈 Rekap Laporan & Unduh Data")
    report_type = st.selectbox("Pilih Jenis Log", ["Stok Masuk", "Mutasi Gudang", "Riwayat Stock Opname"])
    
    if st.button("Tampilkan Laporan"):
        if report_type == "Stok Masuk":
            data = supabase.table("warehouse_in").select("*, stores(store_name), products(product_name)").execute().data
            if data: st.dataframe(pd.DataFrame(data))
        elif report_type == "Mutasi Gudang":
            data = supabase.table("stock_mutations").select("*, stores(store_name), products(product_name)").execute().data
            if data: st.dataframe(pd.DataFrame(data))
        elif report_type == "Riwayat Stock Opname":
            data = supabase.table("stock_opname").select("*, stores(store_name), products(product_name)").execute().data
            if data: st.dataframe(pd.DataFrame(data))
