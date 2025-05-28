# Lead Cleanup Suite

## Overview
The Lead Cleanup Suite is a comprehensive Streamlit-based application for processing and cleaning lead data. It provides multiple specialized tools for address standardization, DNC phone number management, data formatting, and lead generation workflows. This powerful suite helps clean, organize, and optimize lead data from CSV files with various output formats and processing options.

## Features

### 🏠 **Address Processing**
- Parses addresses using the `usaddress` library
- Expands directional, street type, and unit abbreviations
- Handles PO Box addresses
- Creates standardized address formats with city and state

### 📞 **Enhanced DNC Phone Number Cleaner**
- **Simple DNC Processing**: Remove phone numbers where DNC = 'Y'
- **Complex Pattern Support**: Handle comma-separated phone numbers with corresponding DNC statuses
- **Multi-Column Support**: Process multiple phone columns simultaneously
- **Pattern Examples**:
  - Simple: `Phone: '+1234567890', DNC: 'Y'` → Result: `Phone: ''`
  - Complex: `Phone: '+1111, +2222, +3333', DNC: 'N, Y, N'` → Result: `Phone: '+1111, +3333'`
- **Comprehensive Validation**: Automatic verification of DNC cleaning accuracy

### 🔧 **Data Processing Options**
- **Address + HoNWIncome**: Combine address with homeowner, net worth, and income data
- **ZIP Split**: Split data by ZIP codes with address and phone information
- **File Combiner and Batcher**: Merge multiple files and create manageable batches
- **Sha256**: Generate hashed email data for privacy compliance
- **Full Combined Address**: Comprehensive dataset with complete contact information
- **Phone & Credit Score**: Focus on phone numbers and credit scores with address details
- **Split by State**: Organize data by state for targeted campaigns
- **B2B Job Titles Focus**: Extract business-focused data with job titles and company info
- **Filter by Zip Codes**: Target specific geographic areas
- **Complete Contact Export**: Full contact dataset with all available information

### ⚙️ **Advanced Settings**
- **Auto Address Cleaning**: Automatic address standardization
- **Phone Number Formatting**: Consistent phone number formatting
- **Batch Size Control**: Manage output file sizes (default: 2,000 rows)
- **Multiple Output Formats**: CSV, Excel, and JSON downloads

## Requirements
- Python 3.x
- Required Libraries:
  - `streamlit`
  - `pandas` 
  - `usaddress`
  - `hashlib`
  - `zipfile`
  - `io`
  - `re`

You can install the dependencies using:
```bash
pip install streamlit pandas usaddress
```

## How to Use
1. **Start the application**:
   ```bash
   streamlit run app.py
   ```
2. **Upload your CSV file** containing lead data
3. **Configure settings** in the sidebar (optional):
   - Enable/disable auto address cleaning
   - Enable/disable phone number formatting  
   - Set batch size for large datasets
4. **Select processing option** from the available tools
5. **Configure option-specific settings** as needed
6. **Process your data** and download results in your preferred format

## Supported Data Formats

### Required Columns (varies by processing option)
**Basic Address Processing:**
- `PERSONAL_ADDRESS`, `PERSONAL_CITY`, `PERSONAL_STATE`

**DNC Phone Number Cleaner:**
- Any column with 'DNC' in the name (e.g., `DIRECT_DNC`, `MOBILE_PHONE_DNC`)
- Phone columns: `MOBILE_PHONE`, `DIRECT_NUMBER`, `PERSONAL_PHONE`, `COMPANY_PHONE`, `SKIPTRACE_B2B_PHONE`

**Complete Processing:**
- `FIRST_NAME`, `LAST_NAME`
- `PERSONAL_ADDRESS`, `PERSONAL_CITY`, `PERSONAL_STATE`, `PERSONAL_ZIP`
- Optional: `HOMEOWNER`, `NET_WORTH`, `INCOME_RANGE`, `CHILDREN`, `AGE_RANGE`
- Optional: `PERSONAL_EMAIL`, `BUSINESS_EMAIL`, `LINKEDIN_URL`
- Optional: Phone and DNC columns

### Output Formats
- **CSV**: Standard comma-separated values
- **Excel**: .xlsx format with formatting
- **JSON**: Structured data format
- **ZIP**: Multiple files organized by criteria (ZIP codes, states, etc.)

## DNC Phone Number Cleaner Usage

### Simple DNC Processing
```
Input Data:
MOBILE_PHONE: "+1234567890"
DNC: "Y"

Result:
MOBILE_PHONE: "" (phone removed)
```

### Complex Comma-Separated Processing  
```
Input Data:
MOBILE_PHONE: "+1111111111, +2222222222, +3333333333"
MOBILE_PHONE_DNC: "N, Y, N"

Result: 
MOBILE_PHONE: "+1111111111, +3333333333" (middle phone removed)
```

### Supported DNC Patterns
- **Simple**: `'Y'`, `'N'`, `'YES'`, `'NO'`, `'TRUE'`, `'FALSE'`
- **Complex**: `'N, Y, N'`, `'Y, N, Y, N'` (comma-separated lists)
- **Fallback**: Any value containing 'Y' will trigger phone removal

## Test Files Included
- **`test_production_dnc.csv`**: Ready-to-use test file with real data patterns
- **`test_enhanced_dnc.py`**: Logic validation test suite  
- **`test_real_world_dnc.py`**: Real data pattern simulation
- **`TASK_COMPLETED.md`**: Comprehensive documentation of recent enhancements

## Recent Enhancements (May 2025)
- ✅ **Enhanced DNC Phone Number Cleaner**: Now supports complex comma-separated phone-to-DNC mapping
- ✅ **Runtime Error Fixes**: Resolved pandas Series concatenation issues
- ✅ **Comprehensive Testing**: Added production-ready test suites
- ✅ **Real Data Validation**: Tested with actual user data patterns

## Sample CSV
A sample CSV file can be downloaded [here](https://drive.google.com/file/d/19CdaLPNq7SUY1ROx0RgLdFD9gQI9JrSh/view?usp=sharing).

## Troubleshooting

### Common Issues
1. **Missing Columns**: Ensure your CSV contains the required columns for your selected processing option
2. **DNC Column Not Found**: The app automatically detects columns with 'DNC' in the name
3. **Large Files**: Use the batch size setting to split large datasets into manageable chunks
4. **Phone Format Issues**: Enable "Format Phone Numbers" in settings for consistent formatting

### Performance Tips
- For large files (>10,000 rows), consider using batch processing
- Enable auto address cleaning only when necessary for better performance
- Use ZIP or state splitting for very large datasets

## Acknowledgments
This project utilizes:
- `usaddress` library for parsing and structuring address components
- `streamlit` for the web interface
- `pandas` for data processing and manipulation

## License
This project is licensed under the MIT License.

