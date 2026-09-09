import streamlit as st
import pandas as pd
from supabase import create_client

# Masukkan kredensial Supabase Anda di sini
SUPABASE_URL = https://fkfrgxplzqfgmgkzyqac.supabase.co
SUPABASE_KEY = sb_publishable_66pIXoRT35bWJ0sQwB0ftQ_wnSG5vUj

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📦 Aplikasi Pencatatan Stok Store")
menu = st.sidebar.selectbox("Pilih Menu", ["Dashboard", "Stok Masuk", "Mutasi Gudang", "Stock Opname", "Upload POS Kasir"])

if menu == "Dashboard":
    st.subheader("Daftar Cabang Store")
    res = supabase.table("stores").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data))
    else:
        st.info("Belum ada data store.")

elif menu == "Stok Masuk":
    st.subheader("Input Stok Masuk Gudang")
    
    # Ambil data store & produk untuk pilihan form
    stores = supabase.table("stores").select("*").execute().data
    products = supabase.table("products").select("*").execute().data
    
    if stores and products:
        store_dict = {s['store_name']: s['id'] for s in stores}
        prod_dict = {p['product_name']: p['id'] for p in products}
        
        selected_store = st.selectbox("Pilih Store", list(store_dict.keys()))
        selected_prod = st.selectbox("Pilih Produk", list(prod_dict.keys()))
        qty = st.number_input("Jumlah Masuk", min_value=1, value=10)
        notes = st.text_input("Catatan / Keterangan")
        
        if st.button("Simpan Stok Masuk"):
            # 1. Simpan ke tabel warehouse_in
            supabase.table("warehouse_in").insert({
                "store_id": store_dict[selected_store],
                "product_id": prod_dict[selected_prod],
                "quantity": qty,
                "notes": notes
            }).execute()
            
            # 2. Update stok gudang di tabel inventory_stock
            current_inv = supabase.table("inventory_stock").select("*").eq("store_id", store_dict[selected_store]).eq("product_id", prod_dict[selected_prod]).execute().data
            
            if current_inv:
                old_wh = current_inv[0]['warehouse_stock']
                new_wh = old_wh + qty
                new_final = new_wh + current_inv[0]['operational_stock']
                
                supabase.table("inventory_stock").update({
                    "warehouse_stock": new_wh,
                    "final_stock": new_final
                }).eq("store_id", store_dict[selected_store]).eq("product_id", prod_dict[selected_prod]).execute()
            
            st.success("Stok masuk berhasil disimpan dan gudang terupdate!")

elif menu == "Mutasi Gudang":
    st.subheader("Mutasi Gudang ke Operasional")
    st.write("Fitur pemindahan stok dari gudang ke operasional toko.")

elif menu == "Stock Opname":
    st.subheader("Stock Opname (SO) Operasional")
    st.write("Fitur opname dengan pilihan Update atau Tambah Stok.")

elif menu == "Upload POS Kasir":
    st.subheader("Posting Penjualan (Excel POS)")
    st.write("Fitur upload file rekap penjualan kasir.")
