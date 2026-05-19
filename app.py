import re
import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


st.set_page_config(
    page_title="Sales Dashboard",
    layout="wide"
)

# ============================================================
# DISPLAY MODE
# ============================================================

st.sidebar.header("⚙️ Settings")

display_mode = st.sidebar.radio(
    "Display Mode",
    ["Normal Mode", "Dark Mode"],
    horizontal=True
)

if display_mode == "Dark Mode":
    chart_bg = "#0E1117"
    paper_bg = "#0E1117"
    font_color = "white"

    st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { background-color: #111827; color: white; }

    div[data-testid="stMetric"] {
        background-color: #1F2937;
        padding: 10px;
        border-radius: 12px;
        border: 1px solid #374151;
    }

    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] div {
        color: white !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

else:
    chart_bg = "white"
    paper_bg = "white"
    font_color = "black"

    st.markdown("""
    <style>
    .stApp { background-color: white; color: black; }
    [data-testid="stSidebar"] { background-color: #F3F4F6; color: black; }

    div[data-testid="stMetric"] {
        background-color: #F9FAFB;
        padding: 10px;
        border-radius: 12px;
        border: 1px solid #D1D5DB;
    }

    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] div {
        color: black !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: black !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

logo_path = Path(__file__).parent / "logo.png"

col_logo, col_title = st.columns([1, 6])

with col_logo:
    if logo_path.exists():
        st.image(str(logo_path), width=130)

with col_title:
    st.title(" Sales Dashboard")
    st.caption("Customer | Brand | Category | Quantity | Sales | Comparison")


# ============================================================
# CLEANING FUNCTIONS
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_amount(value):
    if pd.isna(value):
        return 0.0

    value = str(value)
    value = value.replace("AED", "")
    value = value.replace(",", "")
    value = value.replace("~", "")
    value = value.replace("'", "")
    value = value.strip()

    if value in ["", "-", "nan", "None"]:
        return 0.0

    try:
        return float(value)
    except Exception:
        return 0.0


def clean_qty(value):
    if pd.isna(value):
        return 0.0

    value = str(value)
    value = value.replace("~", "")
    value = value.replace(",", "")
    value = value.replace("'", "")
    value = value.strip()

    if value in ["", "-", "nan", "None"]:
        return 0.0

    try:
        return float(value)
    except Exception:
        return 0.0

def apply_chart_layout(fig):
    fig.update_layout(
        plot_bgcolor=chart_bg,
        paper_bgcolor=paper_bg,
        font=dict(color=font_color),
        title_font=dict(color=font_color),
        legend_font=dict(color=font_color),

        colorway=[
            "#00BFFF",
            "#1E90FF",
            "#4169E1",
            "#00CED1",
            "#5DADE2"
        ]
    )

    fig.update_xaxes(color=font_color)
    fig.update_yaxes(color=font_color)

    return fig



def format_table_numbers(df_to_format, cols):
    df_display = df_to_format.copy()
    for col in cols:
        if col in df_display.columns:
            df_display[col] = (
                df_display[col]
                .round(0)
                .astype(int)
                .map("{:,}".format)
            )
    return df_display


# ============================================================
# LOAD ZIP FILE
# ============================================================

@st.cache_data
def load_zip_file(zip_path):
    all_data = []

    with zipfile.ZipFile(zip_path, "r") as z:
        csv_files = [f for f in z.namelist() if f.lower().endswith(".csv")]

        for file in csv_files:
            with z.open(file) as f:
                raw_df = pd.read_csv(f)

            raw_df.columns = [str(c).strip() for c in raw_df.columns]

            current_customer = ""

            for _, row in raw_df.iterrows():
                item_name = clean_text(row.get("Item Name", ""))
                brand = clean_text(row.get("Brand", ""))
                product_brand = clean_text(row.get("Product Brand", ""))
                category = clean_text(row.get("Category", ""))
                category_name = clean_text(row.get("Category Name", ""))
                sku = clean_text(row.get("SKU", ""))
                barcode = clean_text(row.get("BARCODE", ""))

                if item_name == "":
                    continue

                item_upper = item_name.upper()

                # Remove unwanted rows before customer detection
                if any(x in item_upper for x in [
                    "SALES RETURN",
                    "SALESRETURN",
                    "RETURN",
                    "DISCOUNT",
                    "POP",
                    "SHOPPING BAG",
                    "SHOPPING BAGS",
                    "BAG",
                    "BAGS",
                ]):
                    continue

                # Customer name is coming in Item Name column
                is_customer_row = (
                    item_name != ""
                    and brand == ""
                    and product_brand == ""
                    and category == ""
                    and category_name == ""
                    and sku == ""
                    and barcode == ""
                )

                if is_customer_row:
                    current_customer = item_name
                    continue

                if current_customer == "":
                    current_customer = "UNKNOWN CUSTOMER"

                final_brand = brand if brand else product_brand
                final_category = category if category else category_name

                for col in raw_df.columns:
                    if col.startswith("Quantity Sold"):
                        year_match = re.search(r"(\d{4})", col)

                        if not year_match:
                            continue

                        year = int(year_match.group(1))

                        amount_col = col.replace("Quantity Sold", "Amount")
                        avg_col = col.replace("Quantity Sold", "Average Price")
                        amount_without_discount_col = col.replace(
                            "Quantity Sold", "Amount without Discount"
                        )
                        amount_with_tax_col = col.replace(
                            "Quantity Sold", "Amount with Tax"
                        )

                        qty = clean_qty(row.get(col, 0))
                        sales = clean_amount(row.get(amount_col, 0))
                        avg_price = clean_amount(row.get(avg_col, 0))
                        amount_without_discount = clean_amount(
                            row.get(amount_without_discount_col, 0)
                        )
                        amount_with_tax = clean_amount(
                            row.get(amount_with_tax_col, 0)
                        )

                        if qty != 0 or sales != 0:
                            all_data.append({
                                "Customer": current_customer,
                                "Item Name": item_name,
                                "Brand": final_brand,
                                "Category": final_category,
                                "SKU": sku,
                                "Barcode": barcode,
                                "Year": year,
                                "Quantity": qty,
                                "Sales": sales,
                                "Average Price": avg_price,
                                "Amount Without Discount": amount_without_discount,
                                "Amount With Tax": amount_with_tax,
                            })

    result = pd.DataFrame(all_data)

    if not result.empty:
        for col in ["Customer", "Item Name", "Brand", "Category", "SKU", "Barcode"]:
            result[col] = result[col].fillna("").astype(str)

    return result


# ============================================================
# DATA SOURCE - GOOGLE DRIVE AUTO LOAD
# ============================================================

GOOGLE_DRIVE_FILE_ID = "1BsWzaogAs57qH7Z563CypOEy66Zry0mg"


@st.cache_data
def download_google_drive_file(file_id):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url, timeout=60)

    temp_path = Path(__file__).parent / "sales_data_from_drive.zip"

    with open(temp_path, "wb") as f:
        f.write(response.content)

    return temp_path


st.sidebar.header("📁 Data Source")
st.sidebar.info("Sales data loaded automatically from Google Drive")

default_zip = download_google_drive_file(GOOGLE_DRIVE_FILE_ID)

df = load_zip_file(default_zip)

if df.empty:
    st.error("No usable sales data found in the Google Drive ZIP file.")
    st.stop()


# ============================================================
# FINAL EXCLUSIONS
# ============================================================

exclude_category_words = (
    "POP|CASES|CASE|SMALL ACC|SMALL ACC.|SMALL ACCESS|"
    "SPARE PARTS|SHOPPING BAGS|SHOPPING BAG|BAGS|BAG"
)

df = df[
    ~df["Category"].str.upper().str.contains(
        exclude_category_words,
        na=False,
        regex=True
    )
]

exclude_item_words = (
    "SALES RETURN|SALESRETURN|RETURN|DISCOUNT|POP|"
    "CASE|CASES|SHOPPING BAGS|SHOPPING BAG|BAGS|BAG"
)

df = df[
    ~df["Item Name"].str.upper().str.contains(
        exclude_item_words,
        na=False,
        regex=True
    )
]

df = df[
    ~df["Customer"].str.upper().str.contains(
        "SALES RETURN|SALESRETURN|RETURN|DISCOUNT|POP",
        na=False,
        regex=True
    )
]

df = df[
    ~df["Brand"].str.upper().str.contains(
        "POP",
        na=False,
        regex=True
    )
]


# ============================================================
# FILTERS
# ============================================================

st.sidebar.header("🔎 Filters")

years = sorted(df["Year"].dropna().unique())
selected_years = st.sidebar.multiselect(
    "Select Year",
    years,
    default=years
)

customers = sorted(df["Customer"].dropna().unique())
selected_customers = st.sidebar.multiselect(
    "Select Customer",
    customers,
    default=customers
)

brands = sorted(df["Brand"].dropna().unique())
selected_brands = st.sidebar.multiselect(
    "Select Brand",
    brands,
    default=brands
)

categories = sorted(df["Category"].dropna().unique())
selected_categories = st.sidebar.multiselect(
    "Select Category",
    categories,
    default=categories
)

item_search = st.sidebar.text_input("Search Item Name")

filtered = df[
    (df["Year"].isin(selected_years)) &
    (df["Customer"].isin(selected_customers)) &
    (df["Brand"].isin(selected_brands)) &
    (df["Category"].isin(selected_categories))
]

if item_search.strip():
    filtered = filtered[
        filtered["Item Name"].str.contains(item_search, case=False, na=False)
    ]

if filtered.empty:
    st.warning("No data found for selected filters.")
    st.stop()


# ============================================================
# KPI CARDS
# ============================================================

total_sales = filtered["Sales"].sum()
total_qty = filtered["Quantity"].sum()
total_customers = filtered["Customer"].nunique()
total_items = filtered["Item Name"].nunique()

top_brand = (
    filtered.groupby("Brand")["Sales"].sum().sort_values(ascending=False).index[0]
    if not filtered.empty else ""
)

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric("Total Sales", f"{total_sales:,.0f}")

with k2:
    st.metric("Total Qty", f"{total_qty:,.0f}")

with k3:
    st.metric("Customers", f"{total_customers:,}")

with k4:
    st.metric("Items", f"{total_items:,}")

with k5:
    st.metric("Top Brand", top_brand[:8])


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "👤 Customer Drill Down",
    "🏷️ Brand Analysis",
    "📋 Detailed Data",
    "📈 Comparison",
])


# ============================================================
# OVERVIEW
# ============================================================

with tab1:
    c1, c2 = st.columns(2)

    year_sales = filtered.groupby("Year", as_index=False)["Sales"].sum()
    year_sales["Year"] = year_sales["Year"].astype(str)

    fig_year = px.line(
        year_sales,
        x="Year",
        y="Sales",
        markers=True,
        title="Year-wise Sales Trend"
    )
    fig_year.update_xaxes(type="category")
    c1.plotly_chart(apply_chart_layout(fig_year), use_container_width=True)

    category_sales = (
        filtered.groupby("Category", as_index=False)["Sales"]
        .sum()
        .sort_values("Sales", ascending=False)
        .head(15)
    )

    fig_category = px.bar(
        category_sales,
        x="Category",
        y="Sales",
        title="Sales by Category"
    )
    c2.plotly_chart(apply_chart_layout(fig_category), use_container_width=True)

    top_items = (
        filtered.groupby("Item Name", as_index=False)
        .agg({"Sales": "sum", "Quantity": "sum"})
        .sort_values("Sales", ascending=False)
        .head(20)
    )

    fig_items = px.bar(
        top_items,
        x="Sales",
        y="Item Name",
        orientation="h",
        title="Top 20 Items by Sales",
        hover_data=["Quantity"]
    )
    st.plotly_chart(apply_chart_layout(fig_items), use_container_width=True)


# ============================================================
# CUSTOMER DRILL DOWN
# ============================================================

with tab2:
    st.subheader("Customer-wise Drill Down Analysis")

    selected_customer_drill = st.selectbox(
        "Select Customer",
        sorted(filtered["Customer"].unique())
    )

    customer_drill = filtered[
        filtered["Customer"] == selected_customer_drill
    ]

    drill_chart_type = st.radio(
        "Drill Down By",
        ["Brand", "Category", "Item Name"],
        horizontal=True
    )

    drill_data = (
        customer_drill.groupby(["Year", drill_chart_type], as_index=False)
        .agg({"Sales": "sum", "Quantity": "sum"})
        .sort_values(["Year", "Sales"], ascending=[True, False])
    )

    fig_drill = px.bar(
        drill_data,
        x=drill_chart_type,
        y="Sales",
        color=drill_chart_type,
        animation_frame="Year",
        hover_data=["Quantity"],
        title=f"{selected_customer_drill} - Animated Sales Drill Down by {drill_chart_type}"
    )

    fig_drill.update_layout(showlegend=False)

    st.plotly_chart(apply_chart_layout(fig_drill), use_container_width=True)

    drill_display = format_table_numbers(
        drill_data,
        ["Sales", "Quantity"]
    )

    st.dataframe(drill_display, use_container_width=True)

    customer_sales = (
        filtered.groupby("Customer", as_index=False)
        .agg({"Sales": "sum", "Quantity": "sum", "Item Name": "nunique"})
        .rename(columns={"Item Name": "No. of Items"})
        .sort_values("Sales", ascending=False)
    )

    fig_customer = px.bar(
        customer_sales.head(25),
        x="Sales",
        y="Customer",
        orientation="h",
        title="Top 25 Customers by Sales",
        hover_data=["Quantity", "No. of Items"]
    )

    st.plotly_chart(apply_chart_layout(fig_customer), use_container_width=True)

    customer_display = format_table_numbers(
        customer_sales,
        ["Sales", "Quantity", "No. of Items"]
    )

    st.dataframe(customer_display, use_container_width=True)


# ============================================================
# BRAND ANALYSIS
# ============================================================

with tab3:
    brand_sales = (
        filtered.groupby("Brand", as_index=False)
        .agg({"Sales": "sum", "Quantity": "sum", "Customer": "nunique"})
        .rename(columns={"Customer": "No. of Customers"})
        .sort_values("Sales", ascending=False)
    )

    c1, c2 = st.columns(2)

    fig_brand_sales = px.bar(
        brand_sales.head(20),
        x="Brand",
        y="Sales",
        title="Top 20 Brands by Sales"
    )
    c1.plotly_chart(apply_chart_layout(fig_brand_sales), use_container_width=True)

    fig_brand_qty = px.bar(
        brand_sales.head(20),
        x="Brand",
        y="Quantity",
        title="Top 20 Brands by Quantity"
    )
    c2.plotly_chart(apply_chart_layout(fig_brand_qty), use_container_width=True)

    brand_display = format_table_numbers(
        brand_sales,
        ["Sales", "Quantity", "No. of Customers"]
    )

    st.dataframe(brand_display, use_container_width=True)


# ============================================================
# DETAILED DATA
# ============================================================

with tab4:
    show_cols = [
        "Customer",
        "Year",
        "Brand",
        "Category",
        "Item Name",
        "Quantity",
        "Sales",
        "Average Price",
        "Amount Without Discount",
        "Amount With Tax",
        "Barcode",
    ]

    display_table = filtered[show_cols].copy()

    display_table = format_table_numbers(
        display_table,
        [
            "Quantity",
            "Sales",
            "Average Price",
            "Amount Without Discount",
            "Amount With Tax",
        ]
    )

    st.dataframe(
        display_table.sort_values(["Customer", "Year", "Brand"]),
        use_container_width=True,
        height=500
    )

    download_csv = filtered[show_cols].to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download Filtered Data as CSV",
        data=download_csv,
        file_name="truebell_fashion_filtered_sales.csv",
        mime="text/csv"
    )


# ============================================================
# COMPARISON
# ============================================================

with tab5:
    st.subheader("Comparison Analysis")

    comparison_type = st.radio(
        "Comparison Type",
        [
            "Customer vs Customer",
            "Customer Year-wise Comparison",
            "Customer Brand-wise Comparison",
            "Brand Year Comparison"
        ],
        horizontal=True,
        key="comparison_type_main"
    )

    if comparison_type == "Customer vs Customer":

        customer_list = sorted(filtered["Customer"].dropna().unique())

        c1, c2 = st.columns(2)

        with c1:
            customer_1 = st.selectbox(
                "Select Customer 1",
                customer_list,
                index=0,
                key="customer_vs_customer_1"
            )

        with c2:
            customer_2 = st.selectbox(
                "Select Customer 2",
                customer_list,
                index=1 if len(customer_list) > 1 else 0,
                key="customer_vs_customer_2"
            )

        compare_level = st.selectbox(
            "Compare Customer By",
            ["Brand"],
            key="customer_compare_level"
        )

        customer_compare_df = filtered[
            filtered["Customer"].isin([customer_1, customer_2])
        ]

        customer_compare_summary = (
            customer_compare_df
            .groupby(["Customer", compare_level], as_index=False)
            .agg({"Sales": "sum", "Quantity": "sum"})
        )

        fig_customer_compare = px.bar(
            customer_compare_summary,
            x=compare_level,
            y="Sales",
            color="Customer",
            barmode="group",
            title=f"{customer_1} vs {customer_2} - Sales by {compare_level}",
            hover_data=["Quantity"]
        )

        st.plotly_chart(
            apply_chart_layout(fig_customer_compare),
            use_container_width=True
        )

        pivot_customer = customer_compare_summary.pivot_table(
            index=compare_level,
            columns="Customer",
            values="Sales",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        if customer_1 in pivot_customer.columns and customer_2 in pivot_customer.columns:
            pivot_customer["Difference"] = (
                pivot_customer[customer_1] - pivot_customer[customer_2]
            )

        display_customer_compare = pivot_customer.copy()

        for col in display_customer_compare.columns:
            if col != compare_level:
                display_customer_compare[col] = (
                    display_customer_compare[col]
                    .round(0)
                    .astype(int)
                    .map("{:,}".format)
                )

        st.subheader("Customer vs Customer Comparison Table")
        st.dataframe(display_customer_compare, use_container_width=True)

    elif comparison_type == "Customer Year-wise Comparison":

        selected_customer = st.selectbox(
            "Select Customer",
            sorted(filtered["Customer"].dropna().unique()),
            key="customer_yearwise_select"
        )

        customer_year_df = filtered[
            filtered["Customer"] == selected_customer
        ]

        customer_year_summary = (
            customer_year_df
            .groupby("Year", as_index=False)
            .agg({"Sales": "sum", "Quantity": "sum"})
            .sort_values("Year")
        )

        customer_year_summary["Year"] = customer_year_summary["Year"].astype(str)

        fig_customer_year = px.bar(
            customer_year_summary,
            x="Year",
            y="Sales",
            color="Year",
            title=f"{selected_customer} - Year-wise Sales Comparison",
            hover_data=["Quantity"]
        )

        fig_customer_year.update_xaxes(type="category")

        st.plotly_chart(
            apply_chart_layout(fig_customer_year),
            use_container_width=True
        )

        display_customer_year = customer_year_summary.copy()
        display_customer_year["Sales"] = display_customer_year["Sales"].round(0).astype(int).map("{:,}".format)
        display_customer_year["Quantity"] = display_customer_year["Quantity"].round(0).astype(int).map("{:,}".format)

        st.subheader("Customer Year-wise Comparison Table")
        st.dataframe(display_customer_year, use_container_width=True)

    elif comparison_type == "Customer Brand-wise Comparison":

        selected_customer_brand = st.selectbox(
            "Select Customer",
            sorted(filtered["Customer"].dropna().unique()),
            key="customer_brandwise_select"
        )

        customer_brand_df = filtered[
            filtered["Customer"] == selected_customer_brand
        ]

        customer_brand_summary = (
            customer_brand_df
            .groupby(["Brand", "Year"], as_index=False)
            .agg({"Sales": "sum", "Quantity": "sum"})
            .sort_values(["Year", "Sales"], ascending=[True, False])
        )

        customer_brand_summary["Year"] = customer_brand_summary["Year"].astype(str)

        fig_customer_brand = px.bar(
            customer_brand_summary,
            x="Brand",
            y="Sales",
            color="Year",
            barmode="group",
            title=f"{selected_customer_brand} - Brand-wise Year Comparison",
            hover_data=["Quantity"]
        )

        st.plotly_chart(
            apply_chart_layout(fig_customer_brand),
            use_container_width=True
        )

        pivot_customer_brand = customer_brand_summary.pivot_table(
            index="Brand",
            columns="Year",
            values="Sales",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        year_cols = [c for c in pivot_customer_brand.columns if c != "Brand"]

        if len(year_cols) >= 2:
            old_year = year_cols[-2]
            new_year = year_cols[-1]

            pivot_customer_brand["Growth"] = (
                pivot_customer_brand[new_year] - pivot_customer_brand[old_year]
            )

            pivot_customer_brand["Growth %"] = pivot_customer_brand.apply(
                lambda x: (x["Growth"] / x[old_year] * 100)
                if x[old_year] != 0 else 0,
                axis=1
            )

        display_customer_brand = pivot_customer_brand.copy()

        for col in display_customer_brand.columns:
            if col != "Brand" and col != "Growth %":
                display_customer_brand[col] = (
                    display_customer_brand[col]
                    .round(0)
                    .astype(int)
                    .map("{:,}".format)
                )

        if "Growth %" in display_customer_brand.columns:
            display_customer_brand["Growth %"] = (
                display_customer_brand["Growth %"]
                .round(2)
                .astype(str) + "%"
            )

        st.subheader("Customer Brand-wise Comparison Table")
        st.dataframe(display_customer_brand, use_container_width=True)

    elif comparison_type == "Brand Year Comparison":

        selected_brand = st.selectbox(
            "Select Brand",
            sorted(filtered["Brand"].dropna().unique()),
            key="brand_yearwise_select"
        )

        brand_year_df = filtered[
            filtered["Brand"] == selected_brand
        ]

        brand_year_summary = (
            brand_year_df
            .groupby("Year", as_index=False)
            .agg({"Sales": "sum", "Quantity": "sum"})
            .sort_values("Year")
        )

        brand_year_summary["Year"] = brand_year_summary["Year"].astype(str)

        fig_brand_year = px.bar(
            brand_year_summary,
            x="Year",
            y="Sales",
            color="Year",
            title=f"{selected_brand} - Year-wise Sales Comparison",
            hover_data=["Quantity"]
        )

        fig_brand_year.update_xaxes(type="category")

        st.plotly_chart(
            apply_chart_layout(fig_brand_year),
            use_container_width=True
        )

        display_brand_year = brand_year_summary.copy()
        display_brand_year["Sales"] = display_brand_year["Sales"].round(0).astype(int).map("{:,}".format)
        display_brand_year["Quantity"] = display_brand_year["Quantity"].round(0).astype(int).map("{:,}".format)

        st.subheader("Brand Year Comparison Table")
        st.dataframe(display_brand_year, use_container_width=True)