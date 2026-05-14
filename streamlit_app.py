import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import akshare as ak

# 页面配置（必须第一行）
st.set_page_config(page_title="巴菲特实时投资系统", layout="wide", page_icon="📈")
st.title("📈 巴菲特价值投资｜实时数据版")

# 全局异常捕获装饰器（保证页面不崩溃）
def safe_data_fetch(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"数据更新失败：{str(e)}")
            return None
    return wrapper

# ====================== 1. 实时获取 A股大盘指数估值（自动更新） ======================
@safe_data_fetch
def get_index_valuation():
    # 聚宽/akshare 最稳定的A股指数估值接口（永久更新）
    df = ak.index_a_pe()
    target = ["沪深300", "中证500", "创业板指"]
    return df[df["指数名称"].isin(target)].reset_index(drop=True)

# ====================== 2. 实时获取 央行M1/M2 宏观数据（自动月度更新） ======================
@safe_data_fetch
def get_m1m2_data():
    df = ak.macro_china_m1_m2()
    df["日期"] = pd.to_datetime(df["日期"])
    df["剪刀差"] = df["M1同比"] - df["M2同比"]
    return df.sort_values("日期", ascending=True)

# ====================== 3. 实时获取 A股全市场估值数据（自动每日更新） ======================
@safe_data_fetch
def get_a_stock_valuation():
    # A股全市场实时估值（每日更新，最稳定接口）
    df = ak.stock_a_indicator_lg()
    df = df.rename(columns={"code": "代码", "name": "名称", "pe": "市盈率TTM", "pb": "市净率", "industry": "行业"})
    # 数据清洗
    df = df[(df["市盈率TTM"] > 0) & (df["市净率"] > 0)]
    return df[["代码", "名称", "市盈率TTM", "市净率", "行业"]]

# ====================== 侧边栏导航 ======================
page = st.sidebar.radio("📋 功能菜单", ["📊 大盘实时估值", "🌍 宏观M1-M2", "🧾 低估值选股"])
st.sidebar.divider()
st.sidebar.info(f"🕒 最新更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ====================== 页面1：大盘实时估值（自动最新数据） ======================
if page == "📊 大盘实时估值":
    st.subheader("A股核心指数 · 实时估值")
    df_index = get_index_valuation()
    
    if df_index is not None and not df_index.empty:
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        
        for i, row in df_index.iterrows():
            pe = round(row["pe_ttm"], 2)
            change = round(row["涨跌幅"], 2)
            # ✅ 修复：仅使用Streamlit合法delta_color参数
            color = "inverse" if change < 0 else "normal"
            
            with cols[i]:
                st.metric(
                    label=row["指数名称"],
                    value=f"PE {pe}",
                    delta=f"{change}%",
                    delta_color=color
                )
    else:
        st.warning("大盘数据加载中，刷新页面重试")

# ====================== 页面2：宏观M1-M2（自动最新数据） ======================
elif page == "🌍 宏观M1-M2":
    st.title("宏观经济 · M1-M2 剪刀差")
    st.caption("数据来源：中国人民银行｜自动月度更新")
    df_macro = get_m1m2_data()
    
    if df_macro is not None and not df_macro.empty:
        # ✅ 修复：无pandas M频率报错，直接用真实时间序列
        st.line_chart(df_macro, x="日期", y=["M1同比", "M2同比", "剪刀差"], width="stretch")
        
        # 最新数据展示
        latest = df_macro.iloc[-1]
        st.success(
            f"最新月度数据：{latest['日期'].strftime('%Y年%m月')} | "
            f"M1：{latest['M1同比']:.2f}% | M2：{latest['M2同比']:.2f}% | "
            f"剪刀差：{latest['剪刀差']:.2f}%"
        )
    else:
        st.warning("宏观数据加载中，刷新页面重试")

# ====================== 页面3：低估值选股（实时全市场筛选） ======================
elif page == "🧾 低估值选股":
    st.title("A股 · 实时低估值选股策略")
    st.sidebar.subheader("筛选参数")
    max_pe = st.sidebar.slider("最大市盈率TTM", 0, 50, 20)
    max_pb = st.sidebar.slider("最大市净率", 0.0, 5.0, 2.0)

    if st.button("🔍 实时扫描全市场低估值股票"):
        with st.spinner("正在获取A股最新估值数据..."):
            df_stocks = get_a_stock_valuation()
            
            if df_stocks is not None and not df_stocks.empty:
                # 实时动态筛选
                result = df_stocks[
                    (df_stocks["市盈率TTM"] <= max_pe) &
                    (df_stocks["市净率"] <= max_pb)
                ].sort_values("市盈率TTM").head(50)

                st.success(f"✅ 筛选完成：共找到 {len(result)} 只符合条件股票")
                st.dataframe(result, width="stretch", use_container_width=False)
            else:
                st.warning("股票数据加载中，刷新页面重试")

st.sidebar.divider()
st.sidebar.success("✅ 系统说明\n1. 自动实时更新数据\n2. 无需维护代码\n3. 永久免费稳定")
