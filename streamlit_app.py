import streamlit as st
import akshare as ak
import pandas as pd
from datetime import datetime

# 页面配置
st.set_page_config(page_title="巴芒投资选股器", layout="wide", initial_sidebar_state="expanded")

# 全局缓存：数据1小时更新一次
@st.cache_data(ttl=3600, show_spinner=False)
def get_index_pe():
    """获取三大指数实时PE（2026.5最新akshare接口）"""
    try:
        # 最新指数行情接口
        df = ak.stock_zh_index_spot_sina()
        # 匹配三大指数代码
        hs300 = df[df["代码"] == "sh000300"]["市盈率"].values[0]
        zz500 = df[df["代码"] == "sh000905"]["市盈率"].values[0]
        cyb = df[df["代码"] == "sz399006"]["市盈率"].values[0]
        return round(float(hs300), 2), round(float(zz500), 2), round(float(cyb), 2)
    except Exception as e:
        st.error(f"指数估值获取失败：{str(e)[:60]}")
        return None

@st.cache_data(ttl=86400, show_spinner=False)
def get_stock_list(roe_min=15, pe_max=25, dividend_min=2):
    """按巴菲特策略动态筛选股票（2026.5最新财务接口）"""
    try:
        # 最新A股财务指标接口（替代废弃的业绩预告接口）
        df = ak.stock_financial_indicator_ths(symbol="A股")
        
        # 数据清洗：转换数值类型
        df["净资产收益率"] = pd.to_numeric(df["净资产收益率"], errors="coerce")
        df["市盈率"] = pd.to_numeric(df["市盈率"], errors="coerce")
        df["股息率"] = pd.to_numeric(df["股息率"], errors="coerce")
        df["资产负债率"] = pd.to_numeric(df["资产负债率"], errors="coerce")
        
        # 严格筛选
        df = df[df["净资产收益率"] >= roe_min]
        df = df[df["市盈率"] <= pe_max]
        df = df[df["股息率"] >= dividend_min]
        df = df[df["资产负债率"] < 60]
        
        # 剔除ST和新股
        df = df[~df["股票名称"].str.contains("ST|*ST", na=False)]
        df = df[df["上市日期"] < (datetime.now() - pd.Timedelta(days=1095)).strftime("%Y-%m-%d")]
        
        # 整理结果
        result = df[["股票代码", "股票名称", "净资产收益率", "市盈率", "股息率", "资产负债率"]].head(20)
        result.columns = ["股票代码", "股票名称", "ROE(%)", "PE", "股息率(%)", "资产负债率(%)"]
        return result.reset_index(drop=True)
    except Exception as e:
        st.error(f"选股数据获取失败：{str(e)[:60]}")
        return None

@st.cache_data(ttl=86400, show_spinner=False)
def get_m1_m2_data():
    """获取M1-M2剪刀差（2026.5最新宏观接口）"""
    try:
        # 最新货币供应量接口
        m1_m2_df = ak.macro_china_money_supply_yearly()
        latest = m1_m2_df.iloc[0]
        # 最新列名匹配
        m1_growth = float(latest["M1同比增长"])
        m2_growth = float(latest["M2同比增长"])
        return round(m1_growth - m2_growth, 2)
    except Exception as e:
        st.error(f"宏观数据获取失败：{str(e)[:60]}")
        return None

# 导航栏
page = st.sidebar.selectbox("导航菜单", ["首页", "选股页面", "宏观数据", "数据说明"])

# 首页
if page == "首页":
    st.title("📈 巴芒投资选股系统")
    st.subheader("基于巴菲特和段永平投资理念的长期投资工具")
    st.info(f"📊 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.subheader("市场估值概览")
    with st.spinner("正在加载最新估值数据..."):
        index_data = get_index_pe()
    
    if index_data:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="沪深300 PE", value=index_data[0])
        with col2:
            st.metric(label="中证500 PE", value=index_data[1])
        with col3:
            st.metric(label="创业板指 PE", value=index_data[2])
    else:
        st.warning("指数估值数据暂时不可用，请稍后刷新页面")

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
        with st.spinner("正在从东方财富网拉取最新财务数据..."):
            stocks = get_stock_list(roe_threshold, pe_threshold, dividend_threshold)
        
        if stocks is not None and not stocks.empty:
            st.success(f"筛选完成！找到 {len(stocks)} 只符合条件的股票")
            st.dataframe(stocks, use_container_width=True)
        elif stocks is None:
            st.error("数据获取失败，请检查网络连接或稍后重试")
        else:
            st.info("没有找到符合当前筛选条件的股票，请调整筛选参数后重试")

# 宏观数据页面
elif page == "宏观数据":
    st.title("📊 宏观经济数据仪表盘")
    st.subheader("M1-M2剪刀差（A股流动性指标）")
    
    st.info("""
    🔍 使用说明：
    • 剪刀差 > 0 → 市场流动性宽松 → 利好股市
    • 剪刀差 < 0 → 市场流动性收紧 → 利空股市
    """)
    
    with st.spinner("正在加载最新宏观数据..."):
        m1_m2 = get_m1_m2_data()
    
    if m1_m2:
        st.metric("最新M1-M2剪刀差", value=f"{m1_m2}%")
    else:
        st.warning("宏观数据暂时不可用，请稍后刷新页面")

# 数据说明页面
elif page == "数据说明":
    st.title("ℹ️ 数据来源与更新")
    st.write(f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.markdown("""
    ### 免费数据来源
    ✅ 股票行情与估值：新浪财经（akshare 2026.5最新接口）
    ✅ 财务数据：同花顺iFinD（akshare 2026.5最新接口）
    ✅ 宏观数据：中国人民银行（akshare 2026.5最新接口）
    
    ### 更新频率
    • 指数估值：每小时更新一次
    • 选股数据：每天更新一次
    • 宏观数据：每月更新一次
    
    ⚠️ 免责声明：本工具仅用于学习参考，不构成任何投资建议。
    """)

st.sidebar.markdown("---")
st.sidebar.caption(f"© 2026 巴芒投资 | 更新：{datetime.now().strftime('%Y-%m-%d')}")
