import streamlit as st
import geopandas as gpd
import pandas as pd
import zipfile
import os
import shutil
import tempfile

st.title("أداة معالجة وتصدير البيانات المساحية")

uploaded_file = st.file_uploader("ارفع ملف النقاط (GeoJSON أو Zip يحتوي على Shapefile)", type=["zip", "geojson"])

name = st.text_input("الاسم")
national_id = st.text_input("الرقم القومي")
order_no = st.text_input("رقم الطلب")

if uploaded_file and st.button("بدء المعالجة واستخراج الملفات"):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        if uploaded_file.name.lower().endswith(".zip"):
            # فك ضغط الملف أولاً لتفادي خطأ القراءة المباشرة
            extract_dir = os.path.join(tmpdir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # قراءة مجلد Shapefile المفكوك
            gdf = gpd.read_file(extract_dir)
        else:
            gdf = gpd.read_file(input_path)

        # تحويل نظام الإحداثيات واستخراج X و Y
        gdf = gdf.to_crs(epsg=4326)
        gdf['X'] = gdf.geometry.x
        gdf['Y'] = gdf.geometry.y

        # حذف التكرارات بناءً على الإحداثيات
        gdf = gdf.drop_duplicates(subset=['X', 'Y'])

        out_dir = os.path.join(tmpdir, "output")
        os.makedirs(out_dir, exist_ok=True)

        # 1. إنشاء ملف إكسيل
        excel_path = os.path.join(out_dir, "excel.xlsx")
        df = pd.DataFrame(gdf.drop(columns='geometry'))
        df.to_excel(excel_path, index=False)

        # 2. إنشاء ملف النص
        txt_path = os.path.join(out_dir, "info.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"الاسم: {name}\n")
            f.write(f"الرقم القومي: {national_id}\n")
            f.write(f"رقم الطلب: {order_no}\n")
            f.write(f"عدد النقاط المعالجة: {len(gdf)}\n")

        # 3. حفظ طبقة Shapefile المعدلة
        shp_dir = os.path.join(out_dir, "point_layers")
        gdf.to_file(shp_dir, driver="ESRI Shapefile")

        # ضغط المخرجات
        zip_output_path = os.path.join(tmpdir, "final_package.zip")
        shutil.make_archive(zip_output_path.replace('.zip', ''), 'zip', out_dir)

        with open(zip_output_path, "rb") as fp:
            st.success("تمت المعالجة بنجاح!")
            st.download_button(
                label="تحميل الملف المضغوط (ZIP)",
                data=fp,
                file_name=f"Request_{order_no}.zip",
                mime="application/zip"
            )
