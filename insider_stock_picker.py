import requests
from bs4 import BeautifulSoup
import yfinance as yf
import schedule
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email instellingen
EMAIL = "izmnizmnarif@gmx.com"
WACHTWOORD = "UZFX7NKNWKWWBIDO4FZ4"
NAAR_EMAIL = "izmnarif@gmx.com"
SMTP_SERVER = "smtp.gmail.com"  # Of bijvoorbeeld smtp.gmx.com afhankelijk van je provider
SMTP_PORT = 587

# Haal insider aankopen op
def fetch_openinsider():
    url = "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=0&fdr=&td=0&tdr=&sicMin=&sicMax=&sortcol=amount&maxresults=50"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table', class_='tinytable')
    stocks = []
    if table:
        rows = table.find_all('tr')[1:]  # Eerste rij is header
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 10:
                try:
                    amount = int(cols[9].text.replace('$', '').replace(',', ''))
                    if amount >= 500000:
                        ticker = cols[1].text.strip()
                        stocks.append(ticker)
                except:
                    continue
    return stocks

# Haal analist beoordelingen op via Yahoo
def fetch_yahoo_recommendation(ticker):
    try:
        stock = yf.Ticker(ticker)
        recs = stock.recommendations
        if recs is not None and not recs.empty:
            latest = recs.iloc[-1]
            if "Buy" in latest['To Grade']:
                return True
        return False
    except Exception:
        return False

# Haal ZackRank (faken we nu even)
def fetch_zack_fake(ticker):
    # Echte scraping van Zack is lastig, dus faken: we zeggen bijv 70% kans op koopadvies
    import random
    return random.random() < 0.7

# Haal nieuwsberichten op (heel basic scraping)
def fetch_news_sentiment(ticker):
    try:
        url = f"https://finance.yahoo.com/quote/{ticker}/news"
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        headlines = soup.find_all('h3')
        good_news = sum(1 for h in headlines if any(word in h.text.lower() for word in ["beats", "surges", "gains", "strong", "growth"]))
        bad_news = sum(1 for h in headlines if any(word in h.text.lower() for word in ["misses", "drops", "falls", "weak"]))
        return good_news >= bad_news
    except Exception:
        return False

# Bouw eindlijst
def scan_stocks():
    insiders = fetch_openinsider()
    final_stocks = []
    for ticker in insiders:
        yahoo_ok = fetch_yahoo_recommendation(ticker)
        zack_ok = fetch_zack_fake(ticker)
        news_ok = fetch_news_sentiment(ticker)

        if yahoo_ok and zack_ok and news_ok:
            final_stocks.append(ticker)

    return final_stocks

# Stuur email
def send_email(stocks):
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = NAAR_EMAIL
    msg['Subject'] = 'Dagelijkse Aandelenselectie'

    html = "<h3>Geselecteerde Aandelen:</h3><table border=1><tr><th>Ticker</th></tr>"
    for stock in stocks:
        html += f"<tr><td>{stock}</td></tr>"
    html += "</table>"

    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL, WACHTWOORD)
        server.sendmail(EMAIL, NAAR_EMAIL, msg.as_string())
        server.quit()
        print("Email verzonden!")
    except Exception as e:
        print("Fout bij verzenden:", e)

# Scheduler
def job():
    print("Start scan...")
    stocks = scan_stocks()
    if stocks:
        send_email(stocks)
    else:
        print("Geen geschikte aandelen gevonden.")

# 1x direct draaien bij starten
job()

# Daarna elk uur
schedule.every().hour.at(":00").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)