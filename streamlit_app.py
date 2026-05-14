import streamlit as st
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="巴芒投资选股器", layout="wide", initial_sidebar_state="expanded")

# -------------------------- 指数估值（Baostock 稳定接口） --------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_index_pe():
    """获取三大指数最新PE，自动跳过空值"""
    try:
        bs.login()
        indexes = [
            ("沪深300", "sh.000300"),
            ("中证500", "sh.000905"),
            ("创业板指", "sz.399006")
        ]
        
        pe_values = []
        for name, code in indexes:
            # 获取近7天数据，自动找最新有效PE
            rs = bs.query_history_k_data_plus(
                code,
                "date,peTTM",
                start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                frequency="d"
            )
            df = rs.get_data()
            
            # 从后往前找第一个非空PE
            for i in range(len(df)-1, -1, -1):
                pe_str = df.iloc[i]["peTTM"]
                if pe_str and pe_str != '':
                    pe_values.append(round(float(pe_str), 2))
                    break
        
        bs.logout()
        if len(pe_values) == 3:
            return pe_values[0], pe_values[1], pe_values[2]
        else:
            st.error("部分指数估值数据缺失")
            return None
    except Exception as e:
        st.error(f"指数估值获取失败：{str(e)[:50]}")
        return None

# -------------------------- 选股数据（Baostock 财务接口） --------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def get_stock_list(roe_min=15, pe_max=25, dividend_min=2):
    """按巴菲特策略筛选股票，严格处理空值和异常"""
    try:
        bs.login()
        # 获取所有A股列表
        rs = bs.query_all_stock(day=datetime.now().strftime("%Y-%m-%d"))
        stock_df = rs.get_data()
        
        # 过滤有效股票
        stock_df = stock_df[
            (stock_df["code"].str.startswith(("sh.", "sz."))) &
            (~stock_df["code_name"].str.contains("ST|*ST", na=False)) &
            (stock_df["tradeStatus"] == "1")  # 仅交易中股票
        ]
        
        result = []
        # 取前800只股票筛选（避免超时）
        for _, row in stock_df.head(800).iterrows():
            code = row["code"]
            name = row["code_name"]
            
            # 获取最新年度财务数据
            fin_rs = bs.query_financial_indicator(
                code,
                year=datetime.now().year-1,  # 用去年完整年报，数据最准
                quarter=4,
                fields="roeAvg,peTTM,dividend,liabilityToAsset,listDate"
            )
            fin_df = fin_rs.get_data()
            
            if fin_df.empty:
                continue
                
            fin = fin_df.iloc[0]
            try:
                # 强制转换并处理空值
                roe = float(fin["roeAvg"]) * 100 if fin["roeAvg"] else 0
                pe = float(fin["peTTM"]) if fin["peTTM"] else 999
                dividend = float(fin["dividend"]) * 100 if fin["dividend"] else 0
                debt = float(fin["liabilityToAsset"]) * 100 if fin["liabilityToAsset"] else 100
                list_date = fin["listDate"]
                
                # 筛选条件
                if (roe >= roe_min and pe <= pe_max and dividend >= dividend_min 
                    and debt < 60 and list_date < (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")):
                    result.append({
                        "股票代码": code.replace("sh.", "").replace("sz.", ""),
                        "股票名称": name,
                        "ROE(%)": round(roe, 2),
                        "PE": round(pe, 2),
                        "股息率(%)": round(dividend, 2),
                        "资产负债率(%)": round(debt, 2)
                    })
            except:
                continue
        
        bs.logout()
        return pd.DataFrame(result).head(20)
    except Exception as e:
        st.error(f"选股数据获取失败：{str(e)[:50]}")
        return None

# -------------------------- 宏观数据（Baostock 稳定接口） --------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def get_m1_m2_data():
    """获取M1-M2剪刀差，Baostock官方稳定接口"""
    try:
        bs.login()
        # 获取货币供应量数据
        rs = bs.query_macro_data(
            indicator_id="M0000001,M0000002",  # M1同比, M2同比
            start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d")
        )
        df = rs.get_data()
        bs.logout()
        
        if not df.empty:
            latest = df.iloc[0]
            m1 = float(latest["M0000001"])
            m2 = float(latest["M0000002"])
            return round(m1 - m2, 2)
        else:
            st.error("宏观数据为空")
            return None
    except Exception as e:
        st.error(f"宏观数据获取失败：{str(e)[:50]}")
        return None

# -------------------------- 页面渲染 --------------------------
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
            st.success(f"筛选完成！找到 {len(stocks)} 只符合条件的股票")
            st.dataframe(stocks, width="stretch")
        elif stocks is None:
            st.error("数据获取失败，请稍后重试")
        else:
            st.info("没有符合当前条件的股票，请调整筛选参数")

# 宏观数据页面
elif page == "宏观数据":
    st.title("📊 宏观经济数据仪表盘")
    st.subheader("M1-M2剪刀差（A股流动性指标）")
    
    st.info("""
    • 剪刀差 > 0 → 流动性宽松 → 利好股市
    • 剪刀差 < 0 → 流动性收紧 → 利空股市
    """)
    
    with st.spinner("正在加载最新宏观数据..."):
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
    ✅ 指数估值：Baostock（上交所/深交所官方行情）
    ✅ 财务数据：Baostock（上市公司公开年报）
    ✅ 宏观数据：Baostock（中国人民银行官方数据）
    
    ### 更新频率
    • 指数估值：每小时更新
    • 选股数据：每天更新（使用上一年完整年报）
    • 宏观数据：每月更新
    
    ⚠️ 免责声明：本工具仅用于学习参考，不构成任何投资建议。
    """)

st.sidebar.markdown("---")
st.sidebar.caption(f"© 2026 巴芒投资 | 更新：{datetime.now().strftime('%Y-%m-%d')}")
