"""Quick exploration of TenK object API"""

import inspect

from edgar import Company, set_identity

set_identity("YourName your.email@example.com")

# Test with Apple
company = Company("AAPL")
filing = company.get_filings(form="10-K").latest(1)

print(f"Filing type: {type(filing)}")
print(f"Filing: {filing.form} filed {filing.filing_date}")

# Get the object
obj = filing.obj()
print(f"\nObject type: {type(obj)}")
print(f"Object class: {obj.__class__.__name__}")

# List all attributes and methods
print("\n" + "=" * 80)
print("Available Attributes and Methods:")
print("=" * 80)

members = inspect.getmembers(obj)
for name, value in members:
    if not name.startswith("_"):
        member_type = type(value).__name__
        print(f"  {name}: {member_type}")

# Check for common financial data methods
print("\n" + "=" * 80)
print("Testing Common Methods:")
print("=" * 80)

# Test if it has financials attribute
if hasattr(obj, "financials"):
    print(f"✅ obj.financials exists: {type(obj.financials)}")

    # Explore financials object
    if obj.financials:
        print("\nFinancials methods:")
        fin_members = inspect.getmembers(obj.financials)
        for name, value in fin_members:
            if not name.startswith("_") and callable(value):
                print(f"  {name}()")
else:
    print("❌ obj.financials does not exist")

# Test if it has income_statement
if hasattr(obj, "income_statement"):
    print(f"✅ obj.income_statement exists: {type(obj.income_statement)}")
else:
    print("❌ obj.income_statement does not exist")

# Test if it has balance_sheet
if hasattr(obj, "balance_sheet"):
    print(f"✅ obj.balance_sheet exists: {type(obj.balance_sheet)}")
else:
    print("❌ obj.balance_sheet does not exist")

# Test if it has xbrl
if hasattr(obj, "xbrl"):
    print(f"✅ obj.xbrl exists: {type(obj.xbrl)}")

    if obj.xbrl:
        print("\nXBRL methods:")
        xbrl_members = inspect.getmembers(obj.xbrl)
        for name, value in xbrl_members:
            if not name.startswith("_") and callable(value):
                print(f"  {name}()")
else:
    print("❌ obj.xbrl does not exist")

# Try to access financials directly
print("\n" + "=" * 80)
print("Direct Access Tests:")
print("=" * 80)

try:
    # Try accessing financials
    if hasattr(obj, "financials") and obj.financials:
        fin = obj.financials

        # Check for common dataframes
        if hasattr(fin, "income_statement"):
            print(f"✅ financials.income_statement: {type(fin.income_statement)}")
            if fin.income_statement is not None:
                print(f"   Shape: {fin.income_statement.shape if hasattr(fin.income_statement, 'shape') else 'N/A'}")

        if hasattr(fin, "balance_sheet"):
            print(f"✅ financials.balance_sheet: {type(fin.balance_sheet)}")
            if fin.balance_sheet is not None:
                print(f"   Shape: {fin.balance_sheet.shape if hasattr(fin.balance_sheet, 'shape') else 'N/A'}")

        if hasattr(fin, "cash_flow_statement"):
            print(f"✅ financials.cash_flow_statement: {type(fin.cash_flow_statement)}")
            if fin.cash_flow_statement is not None:
                print(
                    f"   Shape: {fin.cash_flow_statement.shape if hasattr(fin.cash_flow_statement, 'shape') else 'N/A'}"
                )

except Exception as e:
    print(f"Error: {e}")
