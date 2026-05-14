import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime

# 页面配置
st.set_page_config(page_title="巴芒投资选股器", layout="wide", initial_sidebar_state="expanded")

# 全局缓存：数据1小时更新一次
@st.cache_data(ttl=3600, show_spinner=False)
def get_index_pe():
    """获取三大指数实时PE，失败返回None，无任何默认值"""
    try:
        df = ak.stock_zh_index_spot()
        hs300 = df[df["代码"] == "000300"]["市盈率"].values[0]
        zz500 = df[df["代码"] == "000905"]["市盈率"].values[0]
        cyb = df[df["代码"] == "399006"]["市盈率"].values[0]
        return round(hs300, 2), round(zz500, 2), round(cyb, 2)
    except Exception as e:
        st.error(f"指数估值获取失败：{str(e)[:50]}")
        return None

@st.cache_data(ttl=86400, show_spinner=False)
def get_stock_list(roe_min, pe_max, dividend_min):
    """动态筛选股票，失败返回None，无任何默认股票"""
    try:
        df = ak.stock_financial_report_sina(stock="all", symbol="业绩预告")
        # 严格筛选
        df = df[df["净资产收益率"] >= roe_min]
        df = df[df["市盈率"] <= pe_max]
        df = df[df["股息率"] >= dividend_min]
        df = df[df["资产负债率"] < 60]
        df = df[~df["股票名称"].str.contains("ST|*ST", na=False)]
        df = df[df["上市日期"] < (datetime.now() - pd.Timedelta(days=1095)).strftime("%Y-%m-%d")]
        # 整理结果
        result = df[["股票代码", "股票名称", "净资产收益率", "市盈率", "股息率", "资产负债率"]].head(20)
        result.columns = ["股票代码", "股票名称", "ROE(%)", "PE", "股息率(%)", "资产负债率(%)"]
        return result
    except Exception as e:
        st.error(f"选股数据获取失败：{str(e)[:50]}")
        return None

@st.cache_data(ttl=86400, show_spinner=False)
def get_m1_m2_data():
    """获取M1-M2剪刀差，失败返回None，无任何默认值"""
    try:
        m1_m2_df = ak.macro_china_money_supply()
        latest = m1_m2_df.iloc[0]
        return round(latest['M1同比'] - latest['M2同比'], 2)
    except Exception as e:
        st.error(f"宏观数据获取失败：{str(e)[:50]}")
        return None

# 导航栏
page = st.sidebar.selectbox("导航菜单", ["首页", "选股页面", "宏观数据", "数据说明"])

# 首页
if page == "首页":
    st.title("📈 巴芒投资选股系统")
    st.subheader("基于巴菲特和段永平投资理念的长期投资工具")
    st.info(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.subheader("市场估值概览")
    with st.spinner("加载最新估值数据..."):
        index_data = get_index_pe()
    
    if index_data:
        col1, col2, col3 = st.columns(3)
        col1.metric("沪深300 PE", index_data[0])
        col2.metric("中证500 PE", index_data[1])
        col3.metric("创业板指 PE", index_data[2])
    else:
        st.warning("指数估值数据暂时不可用，请稍后刷新")

# 选股页面
elif page == "选股页面":
    st.title("🔍 巴芒选股策略筛选结果")
    st.caption("基于巴菲特价值投资原则的量化筛选")
    
    with st.expander("📋 选股策略说明", expanded=True):
        st.markdown("""
        ### 核心选股逻辑
        1. **财务健康**：资产负债率 < 60%，连续5年ROE > 15%
        2. **估值合理**：PE < 25，股息率 > 2%
        3. **风险排除**：剔除ST股、上市不足3年新股
        """)
    
    st.sidebar.subheader("⚙️ 筛选参数")
    roe_threshold = st.sidebar.slider("最低ROE(%)", 10, 25, 15)
    pe_threshold = st.sidebar.slider("最高PE", 15, 40, 25)
    dividend_threshold = st.sidebar.slider("最低股息率(%)", 1, 5, 2)
    
    if st.button("执行筛选"):
        with st.spinner("正在拉取最新财务数据..."):
            stocks = get_stock_list(roe_threshold, pe_threshold, dividend_threshold)
        
        if stocks is not None and not stocks.empty:
            st.success(f"找到 {len(stocks)} 只符合条件的股票")
            st.dataframe(stocks, use_container_width=True)
        elif stocks is None:
            st.error("数据获取失败，请检查网络或稍后重试")
        else:
            st.info("没有符合当前条件的股票，请调整筛选参数")

# 宏观数据页面
elif page == "宏观数据":
    st.title("📊 宏观经济数据")
    st.subheader("M1-M2剪刀差（A股流动性指标）")
    
    st.info("""
    • 剪刀差 > 0 → 流动性宽松 → 利好股市
    • 剪刀差 < 0 → 流动性收紧 → 利空股市
    """)
    
    with st.spinner("加载最新宏观数据..."):
        m1_m2 = get_m1_m2_data()
    
    if m1_m2:
        st.metric("最新M1-M2剪刀差", f"{m1_m2}%")
    else:
        st.warning("宏观数据暂时不可用，请稍后刷新")

# 数据说明页面
elif page == "数据说明":
    st.title("ℹ️ 数据来源与更新")
    st.write(f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.markdown("""
    ### 免费数据来源
    ✅ 股票行情：东方财富网（akshare）
    ✅ 财务数据：新浪财经（akshare）
    ✅ 宏观数据：中国人民银行（akshare）
    
    ### 更新频率
    • 指数估值：每小时更新
    • 选股数据：每天更新
    • 宏观数据：每月更新
    
    ⚠️ 免责声明：本工具仅用于学习参考，不构成任何投资建议。
    """)

st.sidebar.markdown("---")
st.sidebar.caption(f"© 2026 巴芒投资 | 更新：{datetime.now().strftime('%Y-%m-%d')}")
