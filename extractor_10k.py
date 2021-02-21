import re
import sys
import pdb
from bs4 import BeautifulSoup, NavigableString, Tag

def get_10k_items(text_10k):
    """Locates items in a HTML-based Form 10K and extracts the text of every item found and identified risk factors from Item 1A.
    
    Args:
        text: String contents of the Form 10K, either in plaintext format or in HTML.
    Returns:
        Dictionary containing any items found and identified risk factors.
    """
    
    def sanitize(text):
        replacements = [[r'[\u2018\u2019\u201b\u2032]', "'"],
                        [r'[\u201c\u201d\u201e\u2033]', '"'],
                        [r'[\u2013\u2014\u2015]', '-'],
                        [r'\u2017', '_'],
                        [r'\u201a', ','],
                        [r'\u0086', ' '],
                        [r'\u0087', ' '],
                        [r'\u0092', "'"],
                        [r'\u0093', '"'],
                        [r'\u0094', '"'],
                        [r'\u0095', ' '],
                        [r'\u009f', ' '],
                        [r'\u00a0', ' '],
                        [r'\u00b7', ' ']]

        for pair in replacements:
            text = re.sub(pair[0], pair[1], text)
            
        return text.strip()
    
    def is_visual_tag(tag):
        if tag.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'ul', 'ol', 'tr', 'table'):
            return True
        else:
            return False
    def next_sibling_tag(tag):
        """Finds the next sibling of a given tag that is of type Tag only, not NavigableString or Comment"""
        sibling_tag = None
        
        while tag.next_sibling:
            tag = tag.next_sibling
            
            if isinstance(tag, Tag):
                sibling_tag = tag
                break
            
        return sibling_tag
    
    def is_emphasized_tag(tag):
        """Analyzes tag to see if it is visually emphasized and if so, returns True"""
        if len(tag.text) < 5:
            return False
        
        if tag.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'b', 'em', 'strong', 'i', 'u'):
            return True
        
        try:
            style_text = tag['style']
            
            if (re.search(r'font-style\s*:\s*italic', style_text, re.IGNORECASE) or
                    re.search(r'font-weight\s*:\s*bold', style_text, re.IGNORECASE) or
                    re.search(r'text-decoration\s*:\s*underline', style_text, re.IGNORECASE)):
                return True
        except:
            pass
        
        return False
    
    def is_emphasized_recursive(tag):
        """Recursive version of is_emphasized_tag that returns True if it or any child tags are visually emphasized"""
        return is_emphasized_tag(tag) or any([is_emphasized_tag(t) for t in tag.find_all()])
    
    def find_item_header(tags, text_regex):
        """Returns visual header tag of an Item determined by text_regex in tags, or None if not found"""
        for tag in tags:
            if not is_visual_tag(tag):
                continue
            
            # check if the tag text contains regex
            if re.search(text_regex, sanitize(tag.text), re.IGNORECASE) is None:
                continue
            
            # at this point the tag is found. but if the tag is a table row, then
    			# return the whole table to aid in item 1a extraction
            while tag.name == 'tr':
                tag = tag.parent
            
            return tag
        
        return None
    
    def get_item_tags(tags, start_regex, end_regexes):
        """Returns the HTML tags belonging to a 10-K item between the tags found by start_regex and the first end_regexes found"""
        item_header  = find_item_header(tags, start_regex)
        
        for end_regex in end_regexes:
            next_item_header = find_item_header(tags, end_regex)
            
            if next_item_header is not None:
                break
            
        if item_header is None or next_item_header is None:
            return []
        
        item_tags = []
        # first check if they are siblings. if not, then the filing probably puts each page into a div
        # in which case we have to break up the divs
        if next_item_header in item_header.next_siblings:
            for sibling in item_header.next_siblings:
                if sibling != next_item_header:
                    item_tags.append(sibling)
                else:
                    break
        else:
            next_item_found = False
            item_tags.extend(item_header.next_siblings)
            curr_parent_block = next_sibling_tag(item_header.parent)
            
            while curr_parent_block is not None:                
                for child in curr_parent_block.find_all(recursive=False):
                    if child != next_item_header:
                        item_tags.append(child)
                    else:
                        next_item_found = True
                        break
                    
                if next_item_found:
                    break
                
                curr_parent_block = next_sibling_tag(curr_parent_block)
                
            if not next_item_found:
                return []
        
        # Throw away navigable strings and comments
        item_tags = [tag for tag in item_tags if isinstance(tag, Tag)]
        item_tags_clean = []
        
        # clean up list
        for tag in item_tags:
            text = sanitize(tag.text.lower())
            
            if len(text) > 6 and text != 'table of contents':
                item_tags_clean.append(tag)
        
        return item_tags_clean
    
    def get_item_plain_text(text, start_regex, end_regexes):
        """Returns the text belonging to a 10-K item between the lines found by start_regex and the first end_regexes found"""
        text = sanitize(text)
        item_header = re.search(start_regex, text, re.IGNORECASE | re.MULTILINE)
        
        for end_regex in end_regexes:
            next_item_header = re.search(end_regex, text, re.IGNORECASE | re.MULTILINE)
            if next_item_header is not None:
                break
        
        if item_header is None or next_item_header is None:
            return None
        
        if next_item_header.start() <= item_header.end():
            return None
        
        item_text = text[item_header.end():next_item_header.start()]
        
        if len(item_text) < 5:
            return None

        return item_text.strip()
    
    def extract_risk_factors(item_1a_tags):
        tags = item_1a_tags
        
        # delete any non-emphasized leading tags and any emphasized trailing tags so that we are left
        # with list guaranteed to start with emphasized tag and end with non-emphasized tag        
        try:
            while not is_emphasized_recursive(tags[0]):
                tags.pop(0)
            
            while is_emphasized_recursive(tags[-1]):
                tags.pop(-1)
                
        except IndexError:
            return []
        
        risk_factors = []
        rfs_found = 0
        
        while tags:
            # find index of next emphasized block after the first one (index 0 is guaranteed to be emphasized)
            for tag_idx in range(1, len(tags)+1):
                if tag_idx == len(tags) or is_emphasized_recursive(tags[tag_idx]):
                    break
            
            # if tag_idx > 1 then we have an emphasized block followed by one or more non-emphasized blocks
            # meaning that we found a risk factor, so we pop those elements from the list.
            # otherwise if tag_idx = 1 there are back-to-back emphasized blocks so we remove the first block
            # and try again. we repeat process until tag list is empty
            if tag_idx > 1:
                rf_text = ''
                rf_summary_text = None
                
                while tag_idx > 0:
                    tag_text = sanitize(tags[0].text.replace('\n', ' '))
                    
                    if rf_summary_text is None:
                        rf_summary_text = tag_text
                        
                    rf_text += tag_text + ' '
                    tags.pop(0)
                    tag_idx -= 1
                
                risk_factors.append({'rf_text' : rf_text.strip(), 'rf_summary' : rf_summary_text, 'rf_position' : rfs_found})
                rfs_found += 1
            else:
                tags.pop(0)
                
        return risk_factors
    
    def tag_list_to_str(tags):
        text_list = []
        
        for tag in tags:
            try:
                # replace newlines since they don't do anything in HTML format and messes up conversion to text
                text_list.append(sanitize(tag.text.replace('\n', ' ')))
            except AttributeError:
                pass
            
        return '\n'.join(text_list)
    
    def get_alt_filing_period(text):
        # stage 1 regex is more lenient than stage 2, but is only run on the first 1000 chars as the filing period text
        # is always at the top of the document. If stage 1 fails, fall back to a stricter stage 2.
        filing_period_regex_stg_1 = re.compile(r'for\s+the\s+(fiscal\s+)?year[\s\-]+ended(.+?,[ \n]\d{4})', re.IGNORECASE | re.DOTALL)
        filing_period_regex_stg_2 = re.compile(r'for\s+the\s+(fiscal\s+)?year[\s\-]+ended[^\w](.+?, \d{4})', re.IGNORECASE | re.DOTALL)
        date_regex = re.compile(r'([a-z]+)\s+(\d\d?),[ \n](\d{4})', re.IGNORECASE)
        month_dict = {'january' : '01',
                      'february' : '02',
                      'march' : '03',
                      'april' : '04',
                      'may' : '05',
                      'june' : '06',
                      'july' : '07',
                      'august' : '08',
                      'september' : '09',
                      'october' : '10',
                      'november' : '11',
                      'december' : '12'}
        
        # run regexes
        search_result = re.search(filing_period_regex_stg_1, text[:1000])
        
        if not search_result:
            search_result = re.search(filing_period_regex_stg_2, text)
        
        # parse result
        if search_result:
            date_search = re.search(date_regex, search_result.group(2))
            if date_search:
                year = date_search.group(3)
                
                day = date_search.group(2)
                if len(day) == 1:
                    day = '0' + day
                
                month_text = date_search.group(1).lower()
                for k, v in month_dict.items():
                    if k in month_text:
                        month = v
                        break
        
        try:
            return '{}{}{}'.format(year, month, day)
        except:
            return None
        
    def remove_finance_tables(tags):
        tags_html = [str(tag) for tag in tags]
        tags_html = '<html><body>' + ''.join(tags_html) + '</body></html>'
        tags_soup = BeautifulSoup(tags_html, 'lxml')
        
        for tag in tags_soup.find_all('table'):
            num_trs = len(tag.find_all('tr'))
            num_tds = len(tag.find_all('td'))
            
            if num_trs >= 3 and num_tds >= num_trs*2: # most non-finance tables have 2 tr tags
                if (tag.text.count('$') >= 2 or tag.text.count('%') >= 2):
                    tag.extract()
                    continue
                
                # second stage table filtering
                digits_count = len(re.findall(r'\d', tag.text))
                alphanumeric_count = len(re.findall(r'\w', tag.text))
                percent_numbers = digits_count / alphanumeric_count if alphanumeric_count != 0 else 0

                if percent_numbers > 0.35 and len(tag.text) > 80:
                    tag.extract()
                    continue
                
        return tags_soup.body.findChildren(recursive=False)
        
    # Main function start
    href_regex = re.compile(r'^\s*item[^a-z0-9]*\d{1,2}[AB]?', re.IGNORECASE)
    item_1_regex  = r'^\s*item[^a-z0-9]*1[^a-z0-9][^0-9]*business[^0-9]*$'
    item_1A_regex = r'^\s*item[^a-z0-9]*1A[^a-z]*risk[^a-z]*factors?[^a-z0-9]?\s*$'
    item_1B_regex = r'^\s*item[^a-z0-9]*1B[^a-z0-9][^0-9]*(unresolved|staff|comment)[^0-9]*$'
    item_2_regex  = r'^\s*item[^a-z0-9]*2[^a-z0-9][^0-9]*(property|properties)[^0-9]*$'
    item_3_regex  = r'^\s*item[^a-z0-9]*3[^a-z0-9][^0-9]*(legal|proceedings)[^0-9]*$'
    item_4_regex  = r'^\s*item[^a-z0-9]*4[^a-z0-9][^0-9]*(mine|safety)[^0-9]*$'
    item_5_regex  = r'^\s*item[^a-z0-9]*5[^a-z0-9][^0-9]*(equity|stockholder)[^0-9]*$'
    item_6_regex  = r'^\s*item[^a-z0-9]*6[^a-z0-9][^0-9]*(selected|financial|data)[^0-9]*$'
    item_7_regex  = r'^\s*item[^a-z0-9]*7[^a-z0-9][^0-9]*(management|discussion|analysis)[^0-9]*$'
    item_7A_regex = r'^\s*item[^a-z0-9]*7A[^a-z0-9][^0-9]*(quantitative|qualitative|disclosure)[^0-9]*$'
    item_8_regex  = r'^\s*item[^a-z0-9]*8[^a-z0-9][^0-9]*(financial|statements|supplementary|data)[^0-9]*$'
    item_9_regex  = r'^\s*item[^a-z0-9]*9[^a-z0-9][^0-9]*(changes|disagreement|account)[^0-9]*$'
    item_9A_regex = r'^\s*item[^a-z0-9]*9A[^a-z0-9][^0-9]*(control|procedure)[^0-9]*$'
    item_9B_regex = r'^\s*item[^a-z0-9]*9B[^a-z0-9][^0-9]*(other|information)[^0-9]*$'
    item_10_regex = r'^\s*item[^a-z0-9]*10[^a-z0-9][^0-9]*(director|executive|officer|governance)[^0-9]*$'
    item_11_regex = r'^\s*item[^a-z0-9]*11[^a-z0-9][^0-9]*(executive|compensation)[^0-9]*$'
    item_12_regex = r'^\s*item[^a-z0-9]*12[^a-z0-9][^0-9]*(security|beneficial|stockholder|owner|management)[^0-9]*$'
    item_13_regex = r'^\s*item[^a-z0-9]*13[^a-z0-9][^0-9]*(relationship|transaction|director|independence)[^0-9]*$'
    item_14_regex = r'^\s*item[^a-z0-9]*14[^a-z0-9][^0-9]*(principal|accounting|fee|service)[^0-9]*$'
    item_15_regex = r'^\s*item[^a-z0-9]*15[^a-z0-9][^0-9]*(exhibit|schedule|statement)[^0-9]*$'

    item_regex_tuples = {'item_1'  : (item_1_regex , [item_1A_regex, item_1B_regex, item_2_regex]),
                         'item_1a' : (item_1A_regex, [item_1B_regex, item_2_regex]),
                         'item_1b' : (item_1B_regex, [item_2_regex]),
                         'item_2'  : (item_2_regex , [item_3_regex]),
                         'item_3'  : (item_3_regex , [item_4_regex]),
                         'item_4'  : (item_4_regex , [item_5_regex]),
                         'item_5'  : (item_5_regex , [item_6_regex]),
                         'item_6'  : (item_6_regex , [item_7_regex]),
                         'item_7'  : (item_7_regex , [item_7A_regex, item_8_regex]),
                         'item_7a' : (item_7A_regex, [item_8_regex]),
                         'item_8'  : (item_8_regex , [item_9_regex]),
                         'item_9'  : (item_9_regex , [item_9A_regex, item_9B_regex, item_10_regex]),
                         'item_9a' : (item_9A_regex, [item_9B_regex, item_10_regex]),
                         'item_9b' : (item_9B_regex, [item_10_regex]),
                         'item_10' : (item_10_regex, [item_11_regex]),
                         'item_11' : (item_11_regex, [item_12_regex]),
                         'item_12' : (item_12_regex, [item_13_regex]),
                         'item_13' : (item_13_regex, [item_14_regex]),
                         'item_14' : (item_14_regex, [item_15_regex])}
    
    if '<html' in text_10k.lower():
        soup = BeautifulSoup(text_10k, 'lxml') # Use lxml parser for best results.
    
        # remove all a hrefs containing item header text
        for tag in soup.find_all():
            try:
                if tag.name == 'a' and tag['href'].strip() != '' and re.search(href_regex, tag.text) and not tag.has_attr('name'):
                    tag.string = ''
            except KeyError:
                pass
        
        # remove table of contents
        for tag in soup.find_all('table'):
            if len(tag.find_all('tr', recursive=False)) > 12 and tag.text.lower().count('item') > 12:
                tag.extract()
            
        # get whole text of document and sanitize
        whole_text_raw = sanitize(soup.text)
        whole_text = re.sub(r'\n[ \t]*\d+[ \t]*\n', '\n', whole_text_raw)
        results = {'whole_text' : whole_text,
                   'content_type' : 'html'}
            
        all_10k_tags = soup.find_all()
        
        for k, regex_tuple in item_regex_tuples.items():
            item_result = get_item_tags(all_10k_tags, regex_tuple[0], regex_tuple[1])
            if item_result:
                results[k] = tag_list_to_str(item_result)
                results[k+'_no_finance_tables'] = tag_list_to_str(remove_finance_tables(item_result))
                results[f'i_{k}_extraction_algorithm'] = 'html'
                
                continue
    
            item_result_plaintext = get_item_plain_text(results['whole_text'], regex_tuple[0], regex_tuple[1])
            if item_result_plaintext:
                results[k] = item_result_plaintext
                results[f'i_{k}_extraction_algorithm'] = 'text_regex'
                
        item_1a_tags = get_item_tags(all_10k_tags, item_regex_tuples['item_1a'][0], item_regex_tuples['item_1a'][1])
        risk_factors = extract_risk_factors(item_1a_tags)
        
        if risk_factors:
            results['risk_factors'] = risk_factors
            results['num_risk_factors'] = len(risk_factors)
                
    else:
        whole_text_raw = sanitize(text_10k)
        results = {'whole_text' : whole_text_raw,
                   'content_type' : 'plaintext'}
        
        text_10k = re.sub(r'\n[ \t]*\d+[ \t]*\n', '\n', text_10k)
        text_10k = re.sub(r'\n[ \t]*<[Pp][Aa][Gg][Ee]>[ \t]*\n', '\n', text_10k)
        
        for k, regex_tuple in item_regex_tuples.items():
            item_result = get_item_plain_text(text_10k, regex_tuple[0], regex_tuple[1])
            
            if item_result:
                results[k] = item_result
                #TODO: Remove financial tables in plaintext 10K
                results[f'i_{k}_extraction_algorithm'] = 'text_regex'
    
    alt_filing_period = get_alt_filing_period(whole_text_raw)
    if alt_filing_period:
            results['alt_filing_period'] = alt_filing_period

    return results
