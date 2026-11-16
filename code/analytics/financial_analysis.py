import pandas as pd
import numpy as np
from config import RAW_DIR,OUTPUT_DIR
from logger import get_logger
logger = get_logger(__name__)
INPUT_FILE = RAW_DIR / "nse_financial_results.csv"
def analyse_stock_performance():
    df=pd.read_csv(INPUT_FILE)
    df["Date"]=pd.to_datetime(df["Date"])
    df=df.sort_values(["Company","Date"])
    df["Close"]=df.to_numeric(df["Close"],erros="coerce")
    results=[]
    for company,group in df.groupby("Company"):
        group=group.dropna(suset=["Close"].copy())
        group=group.sort_values("Date")
        if(len(group)<2):
            continue
        group["Daily_Return"]=group["Close"].pct_change()
        group["Cumulative_Return"]=((1+group["Daily_return"].fillna(0)).cumprod())
        running_peak=group.close.cummax()
        drawdown=(group["Close"]/running_peak)-1
        daily_returns=group["Daily_Return"].dropna()
        total_return=(group["Close"].iloc(-1)/group["Close"].iloc(0))-1
        annualised_volatility=daily_returns.std()*np.sqrt(252)
        max_drawdown=drawdown.min()
        results.append({
            "Company": company,
            "Start_Date": group["Date"].iloc[0],
            "End_Date": group["Date"].iloc[-1],
            "Total_Return": total_return,
            "Annualised_Volatility": annualised_volatility,
            "Maximum_Drawdown": max_drawdown
        })
        summary=pd.DataFrame(results)

    OUTPUT_DIR.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    summary.to_csv(OUTPUT_DIR/"stock_performance_summary.csv",index=False)
    logger.info("Stock performance analysis completed")

    return summary


if __name__ == "__main__":
    analyse_stock_performance()     
