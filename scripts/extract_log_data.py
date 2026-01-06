"""Extract trading data from Railway logs and create detailed trade history"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def parse_log_file(log_path: str) -> List[Dict]:
    """Parse Railway log file and extract trading data"""
    
    entries = []
    current_entry = {}
    
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        # Extract timestamp
        timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)', line)
        if timestamp_match:
            current_timestamp = timestamp_match.group(1)
        
        # Extract position data from "Found position" line
        if "✅ Found position:" in line:
            match = re.search(r"'size':\s+([\d.]+).*'entry_price':\s+([\d.]+).*'unrealized_pnl':\s+([\d.]+).*'leverage':\s+([\d.]+)", line)
            if match:
                current_entry['timestamp'] = current_timestamp
                current_entry['position_size_eth'] = float(match.group(1))
                current_entry['entry_price'] = float(match.group(2))
                current_entry['unrealized_pnl'] = float(match.group(3))
                current_entry['leverage'] = float(match.group(4))
        
        # Extract position side from "📍 Position" line
        if "📍 Position: LONG" in line or "📍 Position: SHORT" in line:
            match = re.search(r'(LONG|SHORT) ([\d.]+) ETH @ \$([\d.]+)', line)
            if match:
                current_entry['position_side'] = match.group(1)
        
        # Extract account value and margin data from marginSummary
        if "Raw marginSummary:" in line:
            account_match = re.search(r"'accountValue':\s+'([\d.]+)'", line)
            pos_match = re.search(r"'totalNtlPos':\s+'([\d.]+)'", line)
            margin_match = re.search(r"'totalMarginUsed':\s+'([\d.]+)'", line)
            
            if account_match:
                current_entry['equity'] = float(account_match.group(1))
            if pos_match:
                current_entry['position_value_usd'] = float(pos_match.group(1))
            if margin_match:
                current_entry['margin_used'] = float(margin_match.group(1))
        
        # Extract starting equity
        if "Starting Equity:" in line:
            match = re.search(r'Starting Equity:\s+\$([\d.]+)', line)
            if match:
                current_entry['starting_equity'] = float(match.group(1))
        
        # Extract total P&L
        if "Total P&L:" in line:
            match = re.search(r'Total P&L:\s+\$\+?([\d.-]+)\s+\(\+?([\d.-]+)%\)', line)
            if match:
                current_entry['total_pnl'] = float(match.group(1))
                current_entry['total_pnl_pct'] = float(match.group(2))
        
        # Save entry when we hit the end marker (Claude decision or new balance sheet)
        if ("🤖 CLAUDE DECISION:" in line or "📊 BALANCE SHEET" in line) and current_entry and len(current_entry) > 5:
            # Calculate ETH price from position
            if 'position_size_eth' in current_entry and 'position_value_usd' in current_entry:
                if current_entry['position_size_eth'] > 0:
                    current_entry['eth_price'] = current_entry['position_value_usd'] / current_entry['position_size_eth']
            
            # Calculate free collateral
            if 'equity' in current_entry and 'margin_used' in current_entry:
                current_entry['free_collateral'] = current_entry['equity'] - current_entry['margin_used']
            
            entries.append(current_entry.copy())
            current_entry = {}
    
    return entries


def generate_trade_log(entries: List[Dict], output_file: str):
    """Generate detailed trade log JSONL file"""
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"✅ Generated trade log: {output_path}")
    print(f"📊 Total entries: {len(entries)}")


def generate_summary(entries: List[Dict]):
    """Generate summary report"""
    
    if not entries:
        print("❌ No entries found")
        return
    
    print("\n" + "="*80)
    print("📊 TRADING SESSION SUMMARY (6 HOURS)")
    print("="*80)
    
    first = entries[0]
    last = entries[-1]
    
    print(f"\n📅 Time Range:")
    print(f"   Start: {first['timestamp']}")
    print(f"   End:   {last['timestamp']}")
    print(f"   Updates: {len(entries)}")
    
    print(f"\n💰 Performance:")
    print(f"   Starting Equity: ${first.get('starting_equity', 0):.2f}")
    print(f"   Final Equity:    ${last.get('equity', 0):.2f}")
    print(f"   Total P&L:       ${last.get('total_pnl', 0):+.2f} ({last.get('total_pnl_pct', 0):+.2f}%)")
    
    # Calculate ETH price range
    eth_prices = [e.get('eth_price', 0) for e in entries if 'eth_price' in e]
    if eth_prices:
        print(f"\n📈 ETH Price:")
        print(f"   Start: ${eth_prices[0]:.2f}")
        print(f"   End:   ${eth_prices[-1]:.2f}")
        print(f"   High:  ${max(eth_prices):.2f}")
        print(f"   Low:   ${min(eth_prices):.2f}")
        print(f"   Range: ${max(eth_prices) - min(eth_prices):.2f}")
    
    print(f"\n🎯 Position:")
    print(f"   Side: {last.get('position_side', 'N/A')}")
    print(f"   Size: {last.get('position_size_eth', 0):.4f} ETH")
    print(f"   Entry: ${last.get('entry_price', 0):.2f}")
    print(f"   Value: ${last.get('position_value_usd', 0):.2f}")
    print(f"   Leverage: {last.get('leverage', 0):.1f}x")
    print(f"   Margin Used: ${last.get('margin_used', 0):.2f}")
    print(f"   Free Collateral: ${last.get('free_collateral', 0):.2f}")
    
    # Calculate max/min P&L
    pnls = [e.get('total_pnl', 0) for e in entries if 'total_pnl' in e]
    if pnls:
        print(f"\n📉 P&L Range:")
        print(f"   Peak:   ${max(pnls):+.2f}")
        print(f"   Trough: ${min(pnls):+.2f}")
        print(f"   Final:  ${pnls[-1]:+.2f}")
    
    print("\n" + "="*80)
    print("📜 DETAILED ENTRIES TABLE")
    print("="*80)
    print(f"\n{'Time':<20} {'ETH Price':<12} {'Side':<8} {'Size':<10} {'Leverage':<10} {'P&L':<15} {'Equity':<12}")
    print("-" * 110)
    
    for entry in entries:
        time_str = entry.get('timestamp', 'N/A')[11:19] if 'timestamp' in entry else 'N/A'
        eth_price = entry.get('eth_price', 0)
        side = entry.get('position_side', 'N/A')
        size = entry.get('position_size_eth', 0)
        leverage = entry.get('leverage', 0)
        pnl = entry.get('total_pnl', 0)
        pnl_pct = entry.get('total_pnl_pct', 0)
        equity = entry.get('equity', 0)
        
        print(
            f"{time_str:<20} "
            f"${eth_price:<11.2f} "
            f"{side:<8} "
            f"{size:<10.4f} "
            f"{leverage:<10.1f} "
            f"${pnl:+7.2f} ({pnl_pct:+5.2f}%) "
            f"${equity:<11.2f}"
        )
    
    print("\n" + "="*80)
    print(f"📁 Detailed log saved to: data/extracted_trade_log.jsonl")
    print("="*80 + "\n")


def main():
    # Parse the log file
    log_file = "logs.1767465522051.log"
    
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        return
    
    print(f"📖 Parsing log file: {log_file}")
    entries = parse_log_file(log_file)
    
    # Generate JSONL trade log
    generate_trade_log(entries, "data/extracted_trade_log.jsonl")
    
    # Generate summary
    generate_summary(entries)


if __name__ == "__main__":
    main()
