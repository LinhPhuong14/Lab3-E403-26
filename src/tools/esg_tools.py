import requests
from duckduckgo_search import DDGS

def search_real_esg_news(company_name: str) -> str:
    """
    Searches the web for the latest real-time ESG news for a company.
    """
    try:
        # Sử dụng news search thay vì text search để tăng độ nhạy với thời sự thực tế
        results = DDGS().news(f"{company_name} ESG OR sustainability OR environment", max_results=3)
        if not results:
            # Fallback về text search nếu news API tạm thời không khả dụng
            results = DDGS().text(f"{company_name} ESG initiatives issues", max_results=3)
            
        if not results:
            return f"Không tìm thấy dữ liệu tin tức công cộng cập nhật (mới nhất) cho {company_name}."
        
        output = f"Latest ESG News for {company_name}:\n"
        for i, res in enumerate(results, 1):
            title = res.get('title', 'No title')
            body = res.get('body', 'No snippets')
            output += f"{i}. {title}\n   Snippets: {body}\n"
        return output
    except Exception as e:
        return f"Error fetching ESG news: {str(e)}"

def get_stock_price(ticker_symbol: str) -> str:
    """
    Fetches the current real-time stock price of a company via Yahoo Finance public API.
    ticker_symbol must be a valid Yahoo Finance ticker (e.g., AAPL, MSFT, TSLA).
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        meta = data['chart']['result'][0]['meta']
        price = meta['regularMarketPrice']
        currency = meta['currency']
        
        return f"Current Stock Price for {ticker_symbol}: {price} {currency}"
    except Exception as e:
        return f"Error fetching stock price for {ticker_symbol}. Make sure the ticker symbol is correct. Details: {str(e)}"

def fetch_company_wikipedia(company_name: str) -> str:
    """
    Fetches the Wikipedia summary of a company to provide general background context.
    """
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{company_name.replace(' ', '_')}"
        r = requests.get(url, timeout=5)
        if r.status_code == 404:
            return f"Wikipedia page not found directly for {company_name}. Ensure correct spelling."
        r.raise_for_status()
        data = r.json()
        return f"Wikipedia Summary for {company_name}:\n{data.get('extract', 'No extract available.')}"
    except Exception as e:
        return f"Error fetching Wikipedia data: {str(e)}"

def calculate_carbon_footprint(energy_kwh: float, fuel_liters: float) -> str:
    """
    Calculates the estimated carbon footprint in kg CO2e based on energy and fuel consumption.
    """
    energy_co2 = float(energy_kwh) * 0.4
    fuel_co2 = float(fuel_liters) * 2.3
    total_co2 = energy_co2 + fuel_co2
    
    return (f"Carbon Footprint Estimate:\n"
            f"Total: {total_co2:.2f} kg CO2e\n"
            f"- From Energy ({energy_kwh} kWh): {energy_co2:.2f} kg CO2e\n"
            f"- From Fuel ({fuel_liters} L): {fuel_co2:.2f} kg CO2e")
