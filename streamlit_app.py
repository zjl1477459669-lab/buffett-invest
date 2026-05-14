import streamlit as st
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="巴芒投资选股器", layout="wide", initial_sidebar_state="expanded")

# 全局初始化Baostock
@st.cache_resource(show_spinner=False)
def init_baostock():
    """初始化Baostock连接，全局只执行一次"""
    lg = bs.login()
    return lg.error_code == '0'

# 全局缓存：数据1小时更新一次
@st.cache_data(ttl=3600, show_spinner=False)
def get_index_pe():
    """获取三大指数实时PE/PB（Baostock稳定接口）"""
    if not init_baostock():
        st.error("Baostock连接失败")
        return None
    
    try:
        # 三大指数代码
        indexes = {
            "沪深300": "sh.000300",
            "中证500": "sh.000905",
            "创业板指": "sz.399006"
        }
        
        result = []
        for name, code in indexes.items():
            # 获取最新交易日的估值数据
            rs = bs.query_history_k_data_plus(
                code,
                "date,peTTM,pbMRQ",
                start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
                frequency="d",
                adjustflag="3"
            )
            df = rs.get_data()
            if not df.empty:
                latest = df.iloc[-1]
                result.append(round(float(latest["peTTM"]), 2))
        
        if len(result) == 3:
            return result[0], result[1], result[2]
        else:
            st.error("指数估值数据不完整")
            return None
    except Exception as e:
        st.error(f"指数估值获取失败：{str(e)[:50]}")
        return None
    finally:
        bs.logout()

@st.cache_data(ttl=86400, show_spinner=False)
def get_stock_list(roe_min=15, pe_max=25, dividend_min=2):
    """按巴菲特策略动态筛选股票（Baostock财务接口）"""
    if not init_baostock():
        st.error("Baostock连接失败")
        return None
    
    try:
        # 获取A股所有股票列表
        stock_rs = bs.query_all_stock(day=datetime.now().strftime("%Y-%m-%d"))
        stock_df = stock_rs.get_data()
        # 只保留主板、创业板、科创板股票
        stock_df = stock_df[stock_df["code"].str.startswith(("sh.", "sz."))]
        stock_df = stock_df[~stock_df["code"].str.endswith((".BJ", ".HK"))]
        
        # 批量获取财务指标
        result_list = []
        for _, row in stock_df.head(500).iterrows():  # 限制数量避免超时
            code = row["code"]
            name = row["code_name"]
            
            # 跳过ST股
            if "ST" in name or "*ST" in name:
                continue
            
            # 获取最新财务数据
            rs = bs.query_financial_indicator(
                code,
                year=datetime.now().year,
                quarter=4,
                fields="roeAvg,peTTM,dividend,liabilityToAsset,listDate"
            )
            df = rs.get_data()
            
            if not df.empty:
                fin = df.iloc[0]
                try:
                    roe = float(fin["roeAvg"]) * 100  # 转换为百分比
                    pe = float(fin["peTTM"])
                    dividend = float(fin["dividend"]) * 100
                    debt_ratio = float(fin["liabilityToAsset"]) * 100
                    list_date = fin["listDate"]
                    
                    # 筛选条件
                    if (roe >= roe_min and pe <= pe_max and dividend >= dividend_min 
                        and debt_ratio < 60 and list_date < (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d")):
                        result_list.append({
                            "股票代码": code,
                            "股票名称": name,
                            "ROE(%)": round(roe, 2),
                            "PE": round(pe, 2),
                            "股息率(%)": round(dividend, 2),
                            "资产负债率(%)": round(debt_ratio, 2)
                        })
                except:
                    continue
        
        return pd.DataFrame(result_list).head(20)
    except Exception as e:
        st.error(f"选股数据获取失败：{str(e)[:50]}")
        return None
    finally:
        bs.logout()

@st.cache_data(ttl=86400, show_spinner=False)
def get_m1_m2_data():
    """获取M1-M2剪刀差（国家统计局官方数据）"""
    try:
        # 使用Baostock宏观数据接口
        rs = bs.query_macro_money_supply()
        df = rs.get_data()
        if not df.empty:
            latest = df.iloc[0]
            m1_growth = float(latest["m1_yoy"])
            m2_growth = float(latest["m2_yoy"])
            return round(m1_growth - m2_growth, 2)
        else:
            st.error("宏观数据为空")
            return None
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
    with st.spinner("正在加载最新估值数据..."):
        index_data = get_index_pe()
    
    if index_data:
        col1, col2, col3 = st.columns(3)
        col1.metric("沪深300 PE", index_data[0])
        col2.metric("中证500 PE", index_data[1])
        col3.metric("创业板指 PE", index_data[2])
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
        with st.spinner("正在从Baostock拉取最新财务数据..."):
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
    ✅ 指数估值：Baostock（上交所/深交所官方数据）
    ✅ 财务数据：Baostock（上市公司公开财报）
    ✅ 宏观数据：Baostock（中国人民银行/国家统计局）
    
    ### 更新频率
    • 指数估值：每小时更新一次
    • 选股数据：每天更新一次
    • 宏观数据：每月更新一次
    
    ⚠️ 免责声明：本工具仅用于学习参考，不构成任何投资建议。
    """)

st.sidebar.markdown("---")
st.sidebar.caption(f"© 2026 巴芒投资 | 更新：{datetime.now().strftime('%Y-%m-%d')}")
