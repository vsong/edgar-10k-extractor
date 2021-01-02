# edgar-10k-extractor
A simple function I wrote that detects and extracts individual Items as well as Item 1A risk factors from an HTML 10-K filing downloaded from edgar.

Written in Python 3.5.

## Installation
To install, place the file in the same directory as your main script. To install dependencies, run:

```bash
pip install -r requirements.txt
```

## Usage
Simply call the function and pass it a BeautifulSoup object.

Example code that works with 10-Ks extracted using the [secedgar](https://github.com/sec-edgar/sec-edgar) python package:

```python
from extractor_10k import get_10k_items
from bs4 import BeautifulSoup
import json

# Using AAPL's 2013 10-K
with open('0001193125-13-416534.txt', 'r') as f:
    data = f.read()

start = data.index('<TEXT>')
end = data.index('</TEXT>')
form_10k_text = data[start+6:end]
soup = BeautifulSoup(form_10k_text, 'lxml') # Use lxml parser for best results.
results = get_10k_items(soup)

with open('out.json', 'w') as w:
    w.write(json.dumps(results, indent=2))
```

## Output (truncated):
```json
{
  "extractor_version": 202012300,
  "whole_text": "Form 10-K\n\n\nTable of Contents\n \n  UNITED STATES \nSECURITIES AND EXCHANGE COM ...",
  "item_1_text": "Company Background\nThe Company designs, manufactures, and markets mobile communi ...",
  "item_1a_text": "The following discussion of risk factors contains forward-looking statements. Th ...",
  "item_2_text": "The Company's headquarters are located in Cupertino, California. As of September  ...",
  "item_3_text": "The Company is subject to the various legal proceedings and claims discussed belo ...",
  "item_4_text": "Not applicable.\nPART II",
  "item_5_text": "The Company's common stock is traded on the NASDAQ Stock Market LLC under the sym ...",
  "item_6_text": "The information set forth below for the five years ended September 28, 2013, is n ...",
  "item_7_text": "This Item 7, \"Management's Discussion and Analysis of Financial Condition and Re ...",
  "item_7a_text": "Interest Rate and Foreign Currency Risk Management\nThe Company regularly review ...",
  "item_8_text": "Index to Consolidated Financial Statements    Page     Consolidated Statements of ...",
  "item_9a_text": "Evaluation of Disclosure Controls and Procedures\nBased on an evaluation under t ...",
  "item_9b_text": "Not applicable.\nPART III",
  "item_10_text": "The information required by this Item is set forth under the headings \"Director ...",
  "item_11_text": "The information required by this Item is set forth under the heading \"Executive ...",
  "item_12_text": "The information required by this Item is set forth under the headings \"Security ...",
  "item_13_text": "The information required by this Item is set forth under the heading \"Review, A ...",
  "item_14_text": "The information required by this Item is set forth under the subheadings \"Fees  ...",
  "risk_factors": [
    {
      "rf_text": "Global and regional economic conditions could materially adversely affect the Com ...",
      "rf_summary": "Global and regional economic conditions could materially adversely affect the  ...",
      "rf_position": 0
    },
    {
      "rf_text": "Global markets for the Company's products and services are highly competitive and ...",
      "rf_summary": "Global markets for the Company's products and services are highly competitive  ...",
      "rf_position": 1
    },
    {
      "rf_text": "To remain competitive and stimulate customer demand, the Company must successfull ...",
      "rf_summary": "To remain competitive and stimulate customer demand, the Company must successf ...",
      "rf_position": 2
    },
    {
      "rf_text": "The Company depends on the performance of distributors, carriers and other resell ...",
      "rf_summary": "The Company depends on the performance of distributors, carriers and other res ...",
      "rf_position": 3
    },
    {
      "rf_text": "The Company faces substantial inventory and other asset risk in addition to purch ...",
      "rf_summary": "The Company faces substantial inventory and other asset risk in addition to pu ...",
      "rf_position": 4
    },
        ...
    {
      "rf_text": "The Company could be subject to changes in its tax rates, the adoption of new U.S ...",
      "rf_summary": "The Company could be subject to changes in its tax rates, the adoption of new  ...",
      "rf_position": 26
    }
  ],
  "risk_factors_found": 27
}
```
If the extractor can't find an item, the key will be excluded from the result.