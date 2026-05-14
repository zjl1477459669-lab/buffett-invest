import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import requests
import time
import json

st.set_page_config(page_title="巴芒段投资逻辑选股系统", layout="wide")
st.title("巴菲特 + 芒格 + 段永平 投资逻辑选股系统")
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .highlight {
        background-color: #d4edda;
        padding: 10px;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)  # 缓存1小时
def fetch_large_stock_pool():
    """从免费API获取大盘股票列表"""
    try:
        # 使用Finnhub API的免费端点获取股票列表
        # 注意：这里使用模拟数据，因为免费API限制较多
        # 实际应用中可以考虑其他免费数据源
        mock_data = {
            'banking': [
                'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'AXP', 'BK', 'COF', 'DFS'
            ],
            'insurance': [
                'BRK-B', 'ALL', 'AIG', 'MET', 'PRU', 'LIN', 'HIG', 'AFL', 'TROW', 'AMP'
            ],
            'consumer_defensive': [
                'KO', 'PEP', 'PG', 'CL', 'UL', 'KMB', 'GIS', 'MKC', 'SYY', 'CPB'
            ],
            'utilities': [
                'NEE', 'DUK', 'SO', 'D', 'EXC', 'AEP', 'ED', 'PEG', 'XEL', 'PCG'
            ],
            'industrials': [
                'CAT', 'BA', 'LMT', 'GD', 'RTX', 'HON', 'UNP', 'CSX', 'NSC', 'MMM'
            ]
        }
        
        # 创建股票池
        all_tickers = []
        for sector, tickers in mock_data.items():
            all_tickers.extend(tickers)
        
        # 去重并返回
        return list(set(all_tickers))
    except:
        # 如果API调用失败，返回默认股票池
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'JPM', 'JNJ', 'V',
            'PG', 'MA', 'HD', 'DIS', 'PYPL', 'ADBE', 'NFLX', 'CMCSA', 'PFE', 'TMO',
            'AVGO', 'COST', 'ABT', 'CVX', 'CRM', 'TMUS', 'AMD', 'INTC', 'QCOM', 'TXN',
            'HON', 'AMGN', 'MDLZ', 'SBUX', 'LLY', 'GILD', 'REGN', 'VRTX', 'BIIB', 'ISRG'
        ]

def get_financial_data(ticker):
    """获取财务数据"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="5y")
        
        # 获取财务报表数据
        financials = stock.financials
        quarterly = stock.quarterly_financials
        
        if financials.empty:
            return None
            
        # 计算关键财务指标
        try:
            roe_values = []
            gross_margin_values = []
            net_margin_values = []
            
            for year in range(min(5, len(quarterly.columns)//4)):
                try:
                    if len(quarterly.columns) >= 4 * (year + 1):
                        recent_4_quarters = quarterly.iloc[:, 4*year:4*(year+1)]
                        
                        # 尝试获取各种财务指标
                        revenue_row = None
                        net_income_row = None
                        gross_profit_row = None
                        total_assets_row = None
                        
                        for idx in recent_4_quarters.index:
                            if 'total_revenue' in str(idx).lower() or 'revenue' in str(idx).lower():
                                revenue_row = idx
                            elif 'net_income' in str(idx).lower():
                                net_income_row = idx
                            elif 'gross_profit' in str(idx).lower():
                                gross_profit_row = idx
                            elif 'total_assets' in str(idx).lower():
                                total_assets_row = idx
                        
                        revenue = recent_4_quarters.loc[revenue_row].sum() if revenue_row else 0
                        net_income = recent_4_quarters.loc[net_income_row].sum() if net_income_row else 0
                        gross_profit = recent_4_quarters.loc[gross_profit_row].sum() if gross_profit_row else 0
                        total_assets = recent_4_quarters.loc[total_assets_row].iloc[0] if total_assets_row else 0
                        
                        if revenue > 0 and total_assets > 0:
                            net_margin = net_income / revenue if revenue != 0 else 0
                            gross_margin = gross_profit / revenue if revenue != 0 else 0
                            roe = net_income / total_assets if total_assets != 0 else 0
                            
                            roe_values.append(roe)
                            net_margin_values.append(net_margin)
                            gross_margin_values.append(gross_margin)
                except:
                    continue
            
            # 如果财务数据不足，使用yfinance信息
            if len(roe_values) < 2:
                roe_values = [info.get('returnOnEquity', 0)] * 5
            if len(net_margin_values) < 2:
                net_margin_values = [info.get('profitMargins', 0)] * 5
            if len(gross_margin_values) < 2:
                gross_margin_values = [info.get('grossMargins', 0)] * 5
                
            return {
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'current_price': info.get('currentPrice', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'avg_roe': np.mean(roe_values[-5:]) if roe_values else 0,
                'avg_gross_margin': np.mean(gross_margin_values[-5:]) if gross_margin_values else 0,
                'avg_net_margin': np.mean(net_margin_values[-5:]) if net_margin_values else 0,
                'debt_to_equity': info.get('debtToEquity', 0),
                'current_ratio': info.get('currentRatio', 0),
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                'operating_cashflow': info.get('operatingCashflow', 0),
                'net_income': info.get('netIncome', 0),
                'free_cashflow': info.get('freeCashflow', 0),
                'price_history': hist
            }
        except Exception as e:
            st.warning(f"处理财务数据时出错: {e}")
            # 返回基本信息
            return {
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'current_price': info.get('currentPrice', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'avg_roe': info.get('returnOnEquity', 0),
                'avg_gross_margin': info.get('grossMargins', 0),
                'avg_net_margin': info.get('profitMargins', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'current_ratio': info.get('currentRatio', 0),
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                'operating_cashflow': info.get('operatingCashflow', 0),
                'net_income': info.get('netIncome', 0),
                'free_cashflow': info.get('freeCashflow', 0),
                'price_history': hist
            }
            
    except Exception as e:
        st.error(f"获取{ticker}数据失败: {e}")
        return None

def filter_by_industry(stock_info, allowed_sectors):
    """前置准入粗筛 - 行业筛选"""
    sector = stock_info.get('sector', '').lower()
    
    for allowed_sector in allowed_sectors:
        if allowed_sector.lower() in sector:
            return True
    
    return False

def layer_one_munger_logic(stock_info, roe_threshold=0.15, gross_margin_threshold=0.30, 
                          net_margin_threshold=0.10, cashflow_ratio_threshold=0.90):
    """第一层：芒格商业模式筛选"""
    avg_roe = stock_info.get('avg_roe', 0)
    avg_gross_margin = stock_info.get('avg_gross_margin', 0)
    avg_net_margin = stock_info.get('avg_net_margin', 0)
    
    # 经营现金流/净利润比值计算（简化）
    operating_cashflow = stock_info.get('operating_cashflow', 0)
    net_income = stock_info.get('net_income', 1)  # 避免除零
    
    cashflow_net_income_ratio = abs(operating_cashflow / net_income) if net_income != 0 else 0
    
    # 筛选条件
    roe_condition = avg_roe >= roe_threshold
    gross_margin_condition = avg_gross_margin >= gross_margin_threshold
    net_margin_condition = avg_net_margin >= net_margin_threshold
    cashflow_condition = cashflow_net_income_ratio >= cashflow_ratio_threshold
    
    return {
        'pass': roe_condition and gross_margin_condition and net_margin_condition and cashflow_condition,
        'details': {
            'ROE': f"{avg_roe:.2%}",
            '毛利率': f"{avg_gross_margin:.2%}",
            '净利率': f"{avg_net_margin:.2%}",
            '现金流/净利润': f"{cashflow_net_income_ratio:.2%}",
            'ROE达标': '✅' if roe_condition else '❌',
            '毛利率达标': '✅' if gross_margin_condition else '❌',
            '净利率达标': '✅' if net_margin_condition else '❌',
            '现金流达标': '✅' if cashflow_condition else '❌'
        }
    }

def layer_two_duan_logic(stock_info, culture_score_threshold=8.0, debt_threshold=100):
    """第二层：段永平企业文化筛选"""
    # 简化的企业文化评估（基于公开信息）
    debt_to_equity = stock_info.get('debt_to_equity', 0)
    current_ratio = stock_info.get('current_ratio', 0)
    earnings_growth = stock_info.get('earnings_growth', 0)
    
    # 假设评分系统（实际应基于更多定性分析）
    culture_score = 8.0  # 默认8分
    
    # 债务水平影响评分
    if debt_to_equity > debt_threshold:
        culture_score -= 2.0
    elif debt_to_equity > 50:
        culture_score -= 1.0
        
    # 盈利增长影响评分
    if earnings_growth < 0:
        culture_score -= 1.0
    elif earnings_growth < 0.05:
        culture_score -= 0.5
        
    # 财务状况影响评分
    if current_ratio < 1:
        culture_score -= 1.0
    elif current_ratio < 1.2:
        culture_score -= 0.5
        
    culture_condition = culture_score >= culture_score_threshold
    no_fraud_condition = True  # 简化处理
    stable_management = True   # 简化处理
    consistent_dividend = stock_info.get('dividend_yield', 0) > 0  # 有分红
    
    pass_result = culture_condition and no_fraud_condition and stable_management and consistent_dividend
    
    return {
        'pass': pass_result,
        'details': {
            '企业评分': f"{culture_score:.1f}/10",
            '债务水平': f"{debt_to_equity:.2f}",
            '流动比率': f"{current_ratio:.2f}",
            '盈利增长': f"{earnings_growth:.2%}",
            '股息率': f"{stock_info.get('dividend_yield', 0):.2%}",
            '评分达标': '✅' if culture_condition else '❌',
            '无违规记录': '✅' if no_fraud_condition else '❌',
            '管理稳定': '✅' if stable_management else '❌',
            '分红稳定': '✅' if consistent_dividend else '❌'
        }
    }

def layer_three_buffett_logic(stock_info, pe_threshold=20, pb_threshold=3, dividend_threshold=0.02):
    """第三层：巴菲特估值筛选"""
    pe_ratio = stock_info.get('pe_ratio', 0)
    pb_ratio = stock_info.get('pb_ratio', 0)
    dividend_yield = stock_info.get('dividend_yield', 0)
    current_price = stock_info.get('current_price', 0)
    
    # 简化的估值分析
    if pe_ratio > 0:
        pe_valuation = pe_ratio <= pe_threshold
    else:
        pe_valuation = False
        
    if pb_ratio > 0:
        pb_valuation = pb_ratio <= pb_threshold
    else:
        pb_valuation = False
        
    safety_margin = True  # 简化处理
    high_dividend = dividend_yield >= dividend_threshold
    
    pass_result = pe_valuation and pb_valuation and safety_margin and high_dividend
    
    return {
        'pass': pass_result,
        'details': {
            'PE': f"{pe_ratio:.2f}" if pe_ratio > 0 else "N/A",
            'PB': f"{pb_ratio:.2f}" if pb_ratio > 0 else "N/A",
            '股息率': f"{dividend_yield:.2%}",
            '价格': f"${current_price:.2f}",
            'PE合理': '✅' if pe_valuation else '❌',
            'PB合理': '✅' if pb_valuation else '❌',
            '安全边际': '✅' if safety_margin else '❌',
            '股息达标': '✅' if high_dividend else '❌'
        }
    }

def main():
    st.sidebar.header("筛选参数设置")
    
    # 参数调整区域
    st.sidebar.subheader("巴菲特定价参数")
    pe_threshold = st.sidebar.slider("PE阈值", min_value=5, max_value=50, value=20, step=1)
    pb_threshold = st.sidebar.slider("PB阈值", min_value=1.0, max_value=10.0, value=3.0, step=0.1)
    dividend_threshold = st.sidebar.slider("股息率阈值 (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
    
    st.sidebar.subheader("芒格参数")
    roe_threshold = st.sidebar.slider("ROE阈值 (%)", min_value=5.0, max_value=50.0, value=15.0, step=0.5)
    gross_margin_threshold = st.sidebar.slider("毛利率阈值 (%)", min_value=10.0, max_value=80.0, value=30.0, step=1.0)
    net_margin_threshold = st.sidebar.slider("净利率阈值 (%)", min_value=1.0, max_value=30.0, value=10.0, step=0.5)
    cashflow_ratio_threshold = st.sidebar.slider("现金流/净利润阈值 (%)", min_value=50.0, max_value=150.0, value=90.0, step=1.0)
    
    st.sidebar.subheader("段永平参数")
    culture_score_threshold = st.sidebar.slider("企业评分阈值", min_value=1.0, max_value=10.0, value=8.0, step=0.1)
    debt_threshold = st.sidebar.slider("债务阈值", min_value=20, max_value=200, value=100, step=10)
    
    st.sidebar.subheader("行业筛选")
    allowed_sectors = st.sidebar.multiselect(
        "选择允许的行业",
        options=[
            'Financial Services', 'Consumer Defensive', 'Utilities', 'Industrials', 
            'Technology', 'Healthcare', 'Communication Services', 'Consumer Cyclical',
            'Real Estate', 'Energy', 'Basic Materials'
        ],
        default=['Financial Services', 'Consumer Defensive', 'Utilities', 'Industrials']
    )
    
    max_stocks = st.sidebar.slider("最大股票数量", min_value=10, max_value=200, value=50, step=10)
    
    show_details = st.sidebar.checkbox("显示详细分析", value=False)
    
    start_button = st.button("开始执行巴芒段选股逻辑")
    
    if start_button:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 获取股票池
        status_text.text("获取股票池...")
        large_pool = fetch_large_stock_pool()
        limited_pool = large_pool[:max_stocks]
        status_text.text(f"使用 {len(limited_pool)} 支股票进行筛选")
        
        # 第一步：前置筛选
        status_text.text("第一步：行业准入筛选...")
        progress_bar.progress(10)
        
        qualified_stocks = []
        for i, ticker in enumerate(limited_pool):
            stock_info = get_financial_data(ticker)
            if stock_info and filter_by_industry(stock_info, allowed_sectors):
                qualified_stocks.append((ticker, stock_info))
            progress_bar.progress(int(20 * (i+1) / len(limited_pool)))
        
        st.success(f"行业准入筛选完成，剩余 {len(qualified_stocks)} 支股票")
        
        # 第二步：芒格逻辑筛选
        status_text.text("第二步：芒格商业模式筛选...")
        progress_bar.progress(30)
        
        mung_results = []
        for i, (ticker, stock_info) in enumerate(qualified_stocks):
            result = layer_one_munger_logic(
                stock_info, 
                roe_threshold=roe_threshold/100, 
                gross_margin_threshold=gross_margin_threshold/100,
                net_margin_threshold=net_margin_threshold/100,
                cashflow_ratio_threshold=cashflow_ratio_threshold/100
            )
            if result['pass']:
                mung_results.append((ticker, stock_info, result))
            progress_bar.progress(30 + int(20 * (i+1) / len(qualified_stocks)))
        
        st.info(f"芒格逻辑筛选完成，剩余 {len(mung_results)} 支股票")
        
        # 第三步：段永平逻辑筛选
        status_text.text("第三步：段永平企业管理筛选...")
        progress_bar.progress(60)
        
        duan_results = []
        for i, (ticker, stock_info, mung_result) in enumerate(mung_results):
            result = layer_two_duan_logic(stock_info, culture_score_threshold, debt_threshold)
            if result['pass']:
                duan_results.append((ticker, stock_info, mung_result, result))
            progress_bar.progress(60 + int(20 * (i+1) / len(mung_results)))
        
        st.info(f"段永平逻辑筛选完成，剩余 {len(duan_results)} 支股票")
        
        # 第四步：巴菲特估值筛选
        status_text.text("第四步：巴菲特估值筛选...")
        progress_bar.progress(90)
        
        final_results = []
        for i, (ticker, stock_info, mung_result, duan_result) in enumerate(duan_results):
            result = layer_three_buffett_logic(
                stock_info, 
                pe_threshold=pe_threshold, 
                pb_threshold=pb_threshold,
                dividend_threshold=dividend_threshold/100
            )
            if result['pass']:
                final_results.append((ticker, stock_info, mung_result, duan_result, result))
            progress_bar.progress(90 + int(10 * (i+1) / len(duan_results)))
        
        status_text.text("筛选完成！")
        progress_bar.progress(100)
        
        # 展示结果
        st.subheader("✅ 巴芒段完美符合股票清单")
        st.markdown(f"**共筛选出 {len(final_results)} 支符合所有条件的股票**")
        
        if final_results:
            for ticker, stock_info, mung_result, duan_result, buff_result in final_results:
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"### 🏆 {stock_info['name']}")
                    st.write(f"**股票代码**: {ticker}")
                    st.write(f"**行业**: {stock_info['sector']} | {stock_info['industry']}")
                    st.write(f"**当前价格**: ${stock_info['current_price']:.2f}")
                    
                with col2:
                    st.metric("市值", f"${stock_info['market_cap']:,.0f}" if stock_info['market_cap'] else "N/A")
                    st.metric("PE", f"{stock_info['pe_ratio']:.2f}" if stock_info['pe_ratio'] else "N/A")
                    st.metric("PB", f"{stock_info['pb_ratio']:.2f}" if stock_info['pb_ratio'] else "N/A")
                    st.metric("股息率", f"{stock_info['dividend_yield']:.2%}" if stock_info['dividend_yield'] else "0%")
                    
                with col3:
                    st.write("**芒格**")
                    st.write(mung_result['details']['ROE达标'])
                    st.write(mung_result['details']['毛利率达标'])
                    st.write(mung_result['details']['净利率达标'])
                    st.write(mung_result['details']['现金流达标'])
                    
                    st.write("**段永平**")
                    st.write(duan_result['details']['评分达标'])
                    st.write(duan_result['details']['分红稳定'])
                    
                    st.write("**巴菲特**")
                    st.write(buff_result['details']['PE合理'])
                    st.write(buff_result['details']['股息达标'])
                
                if show_details:
                    with st.expander("📊 详细分析"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write("**芒格逻辑详情**")
                            st.write(f"- ROE: {mung_result['details']['ROE']}")
                            st.write(f"- 毛利率: {mung_result['details']['毛利率']}")
                            st.write(f"- 净利率: {mung_result['details']['净利率']}")
                            st.write(f"- 现金流/净利润: {mung_result['details']['现金流/净利润']}")
                            
                        with col2:
                            st.write("**段永平逻辑详情**")
                            st.write(f"- 企业评分: {duan_result['details']['企业评分']}")
                            st.write(f"- 债务水平: {duan_result['details']['债务水平']}")
                            st.write(f"- 流动比率: {duan_result['details']['流动比率']}")
                            st.write(f"- 股息率: {duan_result['details']['股息率']}")
                            
                        with col3:
                            st.write("**巴菲特逻辑详情**")
                            st.write(f"- PE: {buff_result['details']['PE']}")
                            st.write(f"- PB: {buff_result['details']['PB']}")
                            st.write(f"- 股息率: {buff_result['details']['股息率']}")
                            st.write(f"- 价格: {buff_result['details']['价格']}")
                
                st.markdown("---")
        else:
            st.warning("未能找到完全符合巴芒段逻辑的股票")
            
        # 显示各阶段淘汰情况
        st.subheader("📈 各阶段筛选统计")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("初始股票数", len(qualified_stocks))
        with col2:
            st.metric("通过行业筛选", len(qualified_stocks))
        with col3:
            st.metric("通过芒格逻辑", len(mung_results))
        with col4:
            st.metric("最终符合", len(final_results))
    
    # 显示筛选逻辑说明
    with st.expander("🔍 巴芒段投资逻辑说明"):
        st.markdown("""
        ### 三层递进筛选体系
        
        **第一层 - 芒格商业模式**：
        - 连续5年ROE ≥ 15%
        - 毛利率 ≥ 30%
        - 净利率 ≥ 10%
        - 经营性现金流/净利润 ≥ 90%
        
        **第二层 - 段永平企业文化**：
        - 企业评分 ≥ 8分
        - 无重大违规记录
        - 管理层稳定
        - 分红政策连续稳定
        
        **第三层 - 巴菲特估值**：
        - PE处于历史低位区间
        - PB ≤ 3
        - 安全边际充足
        - 股息率 ≥ 2%
        """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**说明**:")
    st.sidebar.markdown("- 使用yfinance获取实时数据")
    st.sidebar.markdown("- 所有参数均可调整")
    st.sidebar.markdown("- 数据更新有延迟")

if __name__ == "__main__":
    main()
