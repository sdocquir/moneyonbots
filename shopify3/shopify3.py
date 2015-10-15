__author__ = 'Selim Docquir'

import requests
import sys, traceback
import re
import arrow
import time
import Tkinter as tk
from lxml import html
from selenium import webdriver
from requests.adapters import HTTPAdapter


# Defining options for the GUI
modes = [('Gift Card', 1), ('Credit Card', 2), ('Paypal', 3)]
editions = [('Regular', 1), ('Variant', 2)]
product_types = [('Search by keyword/id', 1), ('Search for new products', 2)]
shipping = [('Shipping', 1), ('No shipping', 2)]
# Defining regex for finding correct edition
regular = "^((?!variant).)*$"
variant = ".*variant.*"

connect_timeout = 10.0
read_timeout = 10.


class ShopifyV3Bot(object):
    def __init__(self):
        '''
        Initialize session, user input and all used variables
        ask user for input
        if payment method is CC, ask user for cc info
        set password and gift cards based on which account the user chose
        :param product_id: input product_id if want to skip finding product based on name
        :return: None
        '''
        self.name           = ''
        self.gateways       = None
        self.gateway_cc     = None
        self.gateway_pp     = None
        self.c              = None
        self.d              = None
        self.payment_url    = None
        self.domain_site    = ''
        self.domain_login   = ''
        self.domain_shopify = ''
        self.domain_paypal  = '.paypal.com'
        self.paypal_url     = None
        self.phantom        = None
        self.list_accounts  = []
        self.list_info      = []
        self.cc_info_raw    = []
        self.product_names  = None
        self.variant_word   = None
        self.session        = requests.Session()
        self.session.mount('http://', requests.adapters.HTTPAdapter(max_retries=20))
        self.firefox         = None                  # will be used for selenium browser if needed
        self.status         = 'Initializing'
        self.cc_info        = []                    # list of cc info from user input
        self.cc_address     = []                    # list of cc address from user input
        self.gift_cards     = []
        self.product_id     = []
        self.product_index  = None
        self.available      = False
        self.product_handle = None
        self.authenticity   = None
        self.checkout_url   = None
        self.order_id       = None
        self.tree           = None
        self.html           = None
        self.email          = None
        self.password       = None
        self.products_limit = 5
        self.refresh_count  = 0                     # keeps track of how many refreshes has been done
        self.refresh_delay  = 0
        self.checkout_delay = 0                     # delays in seconds between applying credit card charges
        self.attempts       = 1                     # count of checkout attempted
        self.mode           = 1
        self.product_type   = 1                     # set modes to default 1
        self.edition_choice = 1
        self.shipping       = 1
        self.mode_human     = None
        self.edition_choice_human = None            # holds human readable choices for outputting to console

    def set_domain(self):
        self.read_info_files()
        self.title = self.name.capitalize() + ' Bot'
        self.products_url = 'http://' + self.domain_site + '/products.json?limit={0}'.format(self.products_limit)
        self.site_url = 'http://' + self.domain_site
        self.cart_url = self.site_url + "/cart"
        self.cart_add_url = self.site_url + "/cart/add"
        self.input_info()                           # call GUI
        self.analyze_input()
        self.print_info()

    def read_info_files(self):
        # open all txt file needed, skip instructions and save content
        with open('shopify3/' + self.name +'/text_files/account_info.txt', 'r') as f:
            skipped_instructions = False
            while skipped_instructions is False:
                position = f.tell()
                if not f.readline().startswith('#'):
                    skipped_instructions = True
                    f.seek(position)
            data = f.readlines()
            for line in data:
                words = line.split()
                self.list_info.append(words)
                self.list_accounts.append(words[0])

        with open('shopify3/' + self.name + '/text_files/cc_info.txt', 'r') as f:
            skipped_instructions = False
            while skipped_instructions is False:
                position = f.tell()
                if not f.readline().startswith('#'):
                    skipped_instructions = True
                    f.seek(position)
            self.cc_info_raw = f.read().splitlines()

        with open('shopify3/' + self.name + '/text_files/product_name.txt', 'r') as f:
            skipped_instructions = False
            while skipped_instructions is False:
                position = f.tell()
                if not f.readline().startswith('#'):
                    skipped_instructions = True
                    f.seek(position)
            self.product_names = f.read().lower()

        with open('shopify3/products_limit.txt', 'r') as f:
            self.products_limit = int(f.read())

        with open('shopify3/variant_word.txt', 'r') as f:
            self.variant_word = f.read().lower()

        with open('shopify3/refresh_delay.txt', 'r') as f:
            self.refresh_delay = float(f.read().lower())

    def analyze_input(self):
        self.keywords = self.product_names.split() # list of keywords to look for

        if self.edition_choice == 1:                # set correct regex based on user input
            self.edition_choice_human = "Regular"
            self.edition_choice_regex = "^((?!{0}).)*$".format(self.variant_word)
        elif self.edition_choice == 2:
            self.edition_choice_human = "Variant"
            self.edition_choice_regex = ".*{0}.*".format(self.variant_word)

        if self.mode == 1:
            self.mode_human = "Gift Card"
        elif self.mode == 2:
            self.mode_human = "Credit Card"
            self.input_cc_info()                    # ask user for cc info if payment method is cc
        elif self.mode == 3:
            self.mode_human = "Paypal"




        for sublist in self.list_info:                   # initialize password and gift cards based on selected account
            if sublist[0] == self.email:
                self.password = sublist[1]
                for x in range(2, len(sublist)):
                    self.gift_cards.append(sublist[x])

    def print_info(self):
        print "Email:           ", self.email
        print "Product:         ", self.keywords
        print "Product Limit:   ", self.products_limit
        print "Edition:         ", self.edition_choice_human
        print "Variant Word:    ", self.variant_word
        print "Mode:            ", self.mode_human
        print "Delay:           ", self.checkout_delay, 'seconds'
        if self.mode == 1:
            for gc in self.gift_cards:
                print "Code:            ", "****"+gc[-4:]
        elif self.mode == 2:
            print "CC:              ", "****"+self.cc_info[2][-4:]


    def full_purchase(self):
        try:
            self.login()
            self.find_product_id()
            print 'Product ID is #               ', self.product_id
            print 'Product Handle is             ', self.product_handle
            print 'Found product at              ', arrow.now().time()
            if type(self.product_id) is list:
                for product_id in self.product_id:
                    self.add_to_cart(product_id)
                    print 'Added to cart product ID #', product_id
            else:
                self.add_to_cart(self.product_id)
            print 'Product in cart at            ', arrow.now().time()
            self.rep_start_checkout()
            print 'Product available at          ', arrow.now().time()
            self.checkout1()
            self.checkout2()
            self.checkout3()
            while self.check_status() == 'Shipping Method Error' and self.attempts <= 5:
                print "Attempt #" + str(self.attempts)
                self.attempts += 1
                self.checkout3()
            print 'Finished process at           ', arrow.now().time()
            if self.check_status() != 'Processing':
                self.save_page('checkout')
            print 'Waiting for Order Page to be loaded ...'
            time.sleep(5) # let order process before checking for order number
            self.load_order_page()
            if self.check_status() == 'Order ID Found':
                print 'Order ID is #\t\t\t\t' + str(self.order_id)
                self.save_page('order')
            else :
                print 'No Order ID found, order failed'
                print 'Opening browser to manually complete order'
                self.open_manual_browser()
        except:
            print 'Error:'
            print traceback.format_exc()
            print 'End Error/'
            self.open_manual_browser()
            raise

    def input_info(self):
        '''
        GUI for user info
        set local variables for radio buttons and string fields
        click exit : exit program
        click submit: save variables to instance variables and close GUI
        :return:
        '''
        root = tk.Tk()
        root.wm_title(self.title)
        acc = tk.StringVar()
        acc.set(self.list_accounts[0])
        mod = tk.IntVar()
        mod.set(1)
        edi = tk.IntVar()
        edi.set(1)
        typ = tk.IntVar()
        typ.set(1)
        prod = tk.StringVar()
        prod.set(self.product_names)
        ship = tk.IntVar()
        ship.set(1)
        id = tk.StringVar()
        id.set('')
        delay = tk.StringVar()
        delay.set('0')

        def tk_exit(self):
            self.email = acc.get()
            self.mode = mod.get()
            self.edition_choice = edi.get()
            self.product_type = typ.get()
            self.shipping = ship.get()
            self.product_names = prod.get()
            temp_id = id.get()
            if temp_id != '':
                self.product_id = temp_id
            self.checkout_delay = int(delay.get())
            root.destroy()

        for txt in self.list_accounts:
            tk.Radiobutton(root, text=txt, indicatoron=0, width=30, padx=30,
                           variable=acc, command=acc.get(), value=txt).grid(column=0)
        for txt, val in modes:
            tk.Radiobutton(root, text=txt, padx=20, variable=mod,
                           command=mod.get(), value=val).grid(row=0, column=val)
        for txt, val in editions:
            tk.Radiobutton(root, text=txt, padx=20, variable=edi,
                           command=edi.get(), value=val).grid(row=1, column=val)
        for txt, val in product_types:
            tk.Radiobutton(root, text=txt, padx=20, variable=typ,
                           command=typ.get(), value=val).grid(row=2, column=val)
        for txt, val in shipping:
            tk.Radiobutton(root, text=txt, padx=20, variable=ship,
                           command=ship.get(), value=val).grid(row=3, column=val)
        tk.Label(root, text="Product ID").grid(row=4, column=1)
        tk.Entry(root, textvariable=id).grid(row=4, column=2)
        tk.Label(root, text="Keywords").grid(row=5, column=1)
        tk.Entry(root, textvariable=prod).grid(row=5, column=2)
        tk.Label(root, text="Delay").grid(row=6, column=1)
        tk.Entry(root, textvariable=delay).grid(row=6, column=2)
        tk.Button(root, text='Submit', command=lambda: tk_exit(self), ).grid(row=7, column=1)
        tk.Button(root, text='Quit', command=sys.exit).grid(row=7, column=2)
        root.mainloop()

    def input_cc_info(self):
        '''
        GUI for CC info
        set local variables to to value taken from cc_info.txt
        exit : exit program
        submit: save local variables to instances variables.
        :return:
        '''
        root = tk.Tk()

        def tk_exit(self):
            self.cc_info = [fname.get(), lname.get(), num.get(), verif.get(), month.get(), year.get()]
            self.cc_address = [add1.get(), add2.get(), city.get(), province.get(), country.get(), zipcode.get(),
                               phone.get()]
            self.checkout_delay = delay_seconds.get()
            root.destroy()

        tk.Label(root, text="First Name").grid(column=0)
        tk.Label(root, text="Last Name").grid(column=0)
        tk.Label(root, text="CC #").grid(column=0)
        tk.Label(root, text="CC Verif").grid(column=0)
        tk.Label(root, text="CC Month").grid(column=0)
        tk.Label(root, text="CC Year").grid(column=0)
        tk.Label(root, text="Delay(seconds)").grid(column=0)
        tk.Label(root, text="Address 1").grid(column=0)
        tk.Label(root, text="Address 2").grid(column=0)
        tk.Label(root, text="City").grid(column=0)
        tk.Label(root, text="State").grid(column=0)
        tk.Label(root, text="Country").grid(column=0)
        tk.Label(root, text="Zip Code").grid(column=0)
        tk.Label(root, text="Phone #").grid(column=0)
        fname = tk.StringVar()
        lname = tk.StringVar()
        num = tk.StringVar()
        verif = tk.StringVar()
        month = tk.StringVar()
        year = tk.StringVar()
        delay_seconds = tk.IntVar()
        add1 = tk.StringVar()
        add2 = tk.StringVar()
        city = tk.StringVar()
        province = tk.StringVar()
        country = tk.StringVar()
        zipcode = tk.StringVar()
        phone = tk.StringVar()
        fname.set(self.cc_info_raw[0])
        lname.set(self.cc_info_raw[1])
        num.set(self.cc_info_raw[2])
        verif.set(self.cc_info_raw[5])
        month.set(self.cc_info_raw[3])
        year.set(self.cc_info_raw[4])
        add1.set(self.cc_info_raw[6])
        city.set(self.cc_info_raw[7])
        province.set(self.cc_info_raw[8])
        country.set(self.cc_info_raw[9])
        zipcode.set(self.cc_info_raw[10])
        phone.set(self.cc_info_raw[11])
        delay_seconds.set(self.checkout_delay)
        tk.Entry(root, textvariable=fname).grid(column=1, row=0)
        tk.Entry(root, textvariable=lname).grid(column=1, row=1)
        tk.Entry(root, textvariable=num).grid(column=1, row=2)
        tk.Entry(root, textvariable=verif).grid(column=1, row=3)
        tk.OptionMenu(root, month, '1', '2', '3', '4', '5', '6',
                                 '7', '8', '9', '10', '11', '12').grid(column=1, row=4)
        tk.OptionMenu(root, year, '2015', '2016', '2017', '2018',
                                '2019', '2020', '2021', '2022').grid(column=1, row=5)
        tk.OptionMenu(root, delay_seconds, '0', '5', '10', '15', '20', '25').grid(column=1, row=6)
        tk.Entry(root, textvariable=add1).grid(column=1, row=7)
        tk.Entry(root, textvariable=add2).grid(column=1, row=8)
        tk.Entry(root, textvariable=city).grid(column=1, row=9)
        tk.Entry(root, textvariable=province).grid(column=1, row=10)
        tk.Entry(root, textvariable=country).grid(column=1, row=11)
        tk.Entry(root, textvariable=zipcode).grid(column=1, row=12)
        tk.Entry(root, textvariable=phone).grid(column=1, row=13)
        tk.Button(root, text='Submit', command=lambda: tk_exit(self), ).grid(row=15, column=0)
        tk.Button(root, text='Quit', command=sys.exit).grid(row=15, column=1)
        root.mainloop()

    def login(self):
        '''
        send POST request to login to mondotees
        :return: None.
        '''
        url = self.site_url + '/account/login'
        r = self.session.get(url)
        self.save_html_tree(r.text)
        url = self.tree.xpath('//form[@id="customer_login"]/@action')
        submit = self.tree.xpath('//input[@type="submit"]/@value')
        login = {'form_type': 'customer_login',
                 'submit': submit[0],
                 'customer[email]': '{0}'.format(self.email),
                 'customer[password]': '{0}'.format(self.password)}
        r = self.session.post(url[0], data=login)
        self.save_html_tree(r.text)


    def find_product_id(self):
        '''
        call correct function based on user input
        :return:
        '''
        if self.product_type == 1:
            self.find_product_id_spec()
        elif self.product_type == 2:
            self.find_product_id_new()

    def find_product_id_new(self):
        '''
        refresh product page, parse json, and look for any new product
        :return:
        '''

        #getting first set of product that subsequent refreshes will be compared to
        r = self.session.get(self.products_url, timeout=(connect_timeout, read_timeout))
        json_data = r.json()
        original_num_products = len(json_data['products'])
        original_product_ids = []
        for i in range(original_num_products):
                original_product_ids.append(json_data['products'][i]['variants'][0]['id'])

        while len(self.product_id) < 1:
            r = self.session.get(self.products_url, timeout=(connect_timeout, read_timeout))
            json_data = r.json()
            num_products = len(json_data['products'])
            for i in range(num_products):
                product_id = json_data['products'][i]['variants'][0]['id']
                if product_id not in original_product_ids:
                    self.product_id.append(product_id)
                    print "Found new product id #", product_id
            self.refresh_count += 1
            print "Refresh #", str(self.refresh_count) + '\r',
            time.sleep(self.refresh_delay)



    def find_product_id_spec(self):
        '''
        refresh product page, parse json and look for product specified
        algorythm: every product found on the json is analysed for keywords
                    each keyword match is worth one point
                    each edition_choice match is worth one point
                    if all products are not equal to zero ( meaning one product matched)
                    we pick the product with the highest score
        change productid  when found
        :return:
        '''
        while len(self.product_id) < 1:
            r = self.session.get(self.products_url, timeout=(connect_timeout, read_timeout))
            json_data = r.json()
            num_products = len(json_data['products'])
            product_handles = []
            product_titles = []
            product_ids = []
            product_scores = []

            # initialize lists with values from json_data
            for i in range(num_products):
                product_handles.append(json_data['products'][i]['handle'])
                product_titles.append(json_data['products'][i]['title'])
                product_ids.append(json_data['products'][i]['variants'][0]['id'])
                product_scores.append(0)  # all products start at score = 0

            # find products that match the keywords
            for i in range(num_products):  # for all the products on the page
                for keyword in self.keywords:  # search handle and title for keywords
                    if re.search(keyword, product_handles[i], re.IGNORECASE):
                        product_scores[i] += 1
                    if re.search(keyword, product_titles[i], re.IGNORECASE):
                        product_scores[i] += 1
            # find products with the highest scores and look for right edition_choice
            for i in range(num_products):
                if product_scores[i] is max(product_scores) and product_scores[i] != 0:
                    if ((re.search(self.edition_choice_regex, product_handles[i], re.IGNORECASE)) or
                        (re.search(self.edition_choice_regex, product_titles[i], re.IGNORECASE))):
                        self.product_id.append(product_ids[i])
                        self.product_handle = product_handles[i]
                        self.product_index = i
                        print product_scores
                        print "Choose product index #", i

            self.refresh_count += 1
            print "Refresh #", str(self.refresh_count) + '\r',
            time.sleep(self.refresh_delay)

    def add_to_cart(self, product_id):
        '''
        add product to cart using supplied id
        :param product_id: string of numbers indicating product_id
        :return:
        '''
        item = {'id': product_id}
        r = self.session.post(self.cart_add_url, data=item, )
        self.save_html_tree(r.text)

    def check_availability(self):
        while self.available == False and self.product_handle is not None:
            r = self.session.get(self.products_url)
            json_data = r.json()
            if json_data['products'][self.product_index]['variants'][0]['available'] is True:
                self.available = True
            else:
                print "Refresh #", str(self.refresh_count) + '\r',
                self.refresh_count += 1

    def rep_start_checkout(self):
        self.start_checkout()
        self.refresh_count = 0
        while self.check_status() == "Item unavailable":
            self.refresh_count += 1
            print "Unavailable Refresh #", str(self.refresh_count) + '\r',
            self.start_checkout()

    def start_checkout(self):
        '''
        send POST request to cart to start checkout
        :return: None
        '''
        checkout = {'checkout': 'Checkout'}
        r = self.session.post(self.cart_url, data=checkout)
        self.save_html_tree(r.text)
        self.get_checkout_url()


    def checkout1(self):
        '''
        find all authenticity info from last html
        parse data for preloaded shipping address
        send POST request with shipping address to go to next step
        :return: None
        '''
        authenticity_token = self.tree.xpath('//input[@name="authenticity_token"]/@value')
        self.authenticity = authenticity_token[0]
        self.address_id = self.tree.xpath('//select[@id="checkout_shipping_address_id"]/option[@value!=""]/@data-properties')
        address_data = {}
        for pair in self.address_id[0].replace('"', '').strip('{}"').split(','):
            k, v = pair.split(':')
            address_data[k] = v
        base_data = {'authenticity_token': self.authenticity,
                     'previous_step': 'contact_information',
                     'step':'shipping_method',
                     'button':'',
                     '_method':'patch',
                     'checkout[email]': self.email,
                     'checkout[shipping_address][id]': address_data['id'],
                     'checkout[shipping_address][first_name]': address_data['first_name'],
                     'checkout[shipping_address][last_name]': address_data['last_name'],
                     'checkout[shipping_address][address1]': address_data['address1'],
                     'checkout[shipping_address][address2]': address_data['address2'],
                     'checkout[shipping_address][city]': address_data['city'],
                     'checkout[shipping_address][province]': address_data['province'],
                     'checkout[shipping_address][country]': address_data['country_name'],
                     'checkout[shipping_address][zip]': address_data['zip'],
                     'checkout[shipping_address][phone]': address_data['phone'],
                     'checkout[client_details][browser_width]': '700',
                     'checkout[client_details][browser_height]': '700'}
        self.get_checkout_url()
        r = self.session.post(self.checkout_url, data=base_data)
        self.save_html_tree(r.text)

    def checkout2(self):
        #refresh page until shipping rates load up
        r = self.session.get(self.checkout_url)
        self.save_html_tree(r.text)
        shipping_rate = self.tree.xpath('//input[@name="checkout[shipping_rate_id]"]/@value')
        sleep_time = 0
        max_retries_ship_rate = 0
        while len(shipping_rate) < 1 and max_retries_ship_rate < 10:
            sleep_time += 1
            max_retries_ship_rate += 1
            time.sleep(sleep_time)
            r = self.session.get(self.checkout_url)
            self.save_html_tree(r.text)
            shipping_rate = self.tree.xpath('//input[@name="checkout[shipping_rate_id]"]/@value')
        shipping_rate = self.tree.xpath('//input[@name="checkout[shipping_rate_id]"]/@value')
        print 'Slept',sleep_time, 'seconds before finding shipping rate'
        print shipping_rate
        data = {'authenticity_token': self.authenticity,
                '_method': 'patch',
                'previous_step': 'shipping_method',
                'step': 'payment_method',
                'button': '',
                'checkout[client_details][browser_width]': '1583',
                'checkout[client_details][browser_height]': '799',}
        data.update({'checkout[shipping_rate_id]': shipping_rate[0]})
        r = self.session.post(self.checkout_url, data=data)
        self.save_html_tree(r.text)

    def apply_gift(self, gc_code):
        '''
        apply gift to last checkout step
        :param gc_code: gift card code in string format
        :return:
        '''
        data = {'authenticity_token': self.authenticity,
                '_method': 'patch',
                'step': 'shipping_and_payment_method',
                'checkout[gift_card][code]': '{0}'.format(gc_code),
                'commit': 'Apply'}
        r = self.session.post(self.checkout_url, data=data)
        self.save_html_tree(r.text)

    def checkout3(self):
        '''
         find payment gateways
         call correct checkout2 function based on user payment method
         if GC : apply gift cards and call checkout2_gift
         If CC : apply delay and call checkout2_cc
        :return:None
        '''
        if self.payment_url is None:
            urls = self.tree.xpath('//form/@action')
            for url in urls:
                if 'sessions' in url:
                    self.payment_url = url
        if self.gateways is None:
            self.gateways = self.tree.xpath('//div/@data-select-gateway')
        if self.c is None:
            self.c = self.tree.xpath('//input[@name="c"]/@value')
        if self.d is None:
            self.d = self.tree.xpath('//input[@name="d"]/@value')
        if len(self.gateways) > 0:
            self.gateway_cc = self.gateways[0]
        if len(self.gateways) > 1:
            self.gateway_pp = self.gateways[1]
        for gc in self.gift_cards:
            self.apply_gift(gc)
            print 'Applied GC', gc
        self.gift_cards = []
        if self.checkout_delay > 0:
            print "Delaying checkout by " + str(self.checkout_delay)
            time.sleep(self.checkout_delay)
            self.checkout_delay = 0
        if self.mode == 1:
            self.checkout3_gift()
        elif self.mode == 2:
            self.checkout3_cc()
        elif self.mode == 3:
            self.checkout3_pp()
            self.paypal_login_phantom()
            self.load_phantom_cookies()
            time.sleep(10)
            self.paypal_checkout_phantom()

    def checkout3_gift(self):
        '''
        send POST request to payment url with free as payment gateway, and same billing address
        :return: None
        '''
        #find shipping rate.
        #if not found, put empty string to pass to dict for post request
        data = {'authenticity_token': self.authenticity,
                'previous_step': 'payment_method',
                'complete': '1',
                'button': '',
                'c': self.c[0],
                'd': self.d[0],
                'checkout[payment_gateway]': 'free',
                'checkout[different_billing_address': 'false',
                'checkout[buyer_accepts_marketing]':'0',
                'checkout[client_details][browser_width]': '1583',
                'checkout[client_details][browser_height]': '799',}
        r = self.session.post(self.payment_url, data=data)
        self.save_html_tree(r.text)

    def checkout3_cc(self):
        '''
        send POST request to payment url using cc payment gateway and supplied user billing address
        :return: None
        '''
        data = {'authenticity_token': self.authenticity,
                'previous_step': 'payment_method',
                'complete': '1',
                'button': '',
                'c': self.c[0],
                'd': self.d[0],
                'checkout[payment_gateway]': self.gateway_cc,
                'checkout[credit_card][name]': (self.cc_info[0] + ' ' + self.cc_info[1]),
                'checkout[credit_card][number]': self.cc_info[2],
                'checkout[credit_card][month]': self.cc_info[4],
                'checkout[credit_card][year]': self.cc_info[5],
                'checkout[credit_card][verification_value]': self.cc_info[3],
                'checkout[different_billing_address': 'true',
                'checkout[billing_address][first_name]': self.cc_info[0],
                'checkout[billing_address][last_name]': self.cc_info[1],
                'checkout[billing_address][address1]': self.cc_address[0],
                'checkout[billing_address][address2]': self.cc_address[1],
                'checkout[billing_address][city]': self.cc_address[2],
                'checkout[billing_address][province]': self.cc_address[3],
                'checkout[billing_address][country]': self.cc_address[4],
                'checkout[billing_address][zip]': self.cc_address[5],
                'checkout[billing_address][phone]': self.cc_address[6],
                'checkout[buyer_accepts_marketing]':'0',
                'checkout[client_details][browser_width]': '1583',
                'checkout[client_details][browser_height]': '799',}
        r = self.session.post(self.payment_url, data=data)
        self.save_html_tree(r.text)

    def checkout3_pp(self):
        '''
        send POST request to payment url using pp payment gateway
        :return: None
        '''
        data = {'authenticity_token': self.authenticity,
                'complete': '1',
                'button': '',
                'previous_step': 'payment_method',
                'c': self.c[0],
                'd': self.d[0],
                'checkout[payment_gateway]': self.gateway_pp,
                'checkout[different_billing_address': 'false',
                'checkout[buyer_accepts_marketing]':'0',
                'checkout[client_details][browser_width]': '1583',
                'checkout[client_details][browser_height]': '799'}
        r = self.session.post(self.payment_url, data=data)
        self.paypal_url = r.url
        self.save_html_tree(r.text)


    def paypal_login_phantom(self):
        self.phantom = webdriver.PhantomJS()
        self.phantom.set_window_size(1280, 720)
        self.phantom.implicitly_wait(10)
        self.phantom.get('https://paypal.com/signin')
        self.phantom.find_element_by_id('email').send_keys(self.email)
        self.phantom.find_element_by_id('password').send_keys('Ulb25826?!+')
        self.phantom.find_element_by_id('btnLogin').click()

    def paypal_checkout_phantom(self):
        self.phantom.get(self.paypal_url)
        time.sleep(10)
        self.save_screenshot('first')
        self.phantom.find_element_by_id('confirmButtonTop').click()
        time.sleep(10)
        self.save_screenshot('second')


    def load_order_page(self):
        '''
        send GET request to checkout_url.
        used when order is successful
        :return: None
        '''
        r = self.session.get(self.checkout_url)
        self.save_html_tree(r.text)

    def save_page(self, description='default'):
        '''
        save file in orders folder using email and checkout url
        :param description: string code for what kind of file needs to be saved
        :return:
        '''
        f = open('shopify3/' + self.name + '/orders/{0}-{1}-{2}.html'.format(self.email[0:7], self.product_id, description), 'w')
        f.write(self.html.encode("UTF-8"))
        f.close()

    def check_status(self):
        '''
        find keywords in last received html, change status accordingly
        :return:None
        '''
        if self.html.find("There was a problem with the selected shipping method") != -1:
            self.status = 'Shipping Method Error'

        elif self.html.find("format is not valid") != -1:
            self.status = 'Invalid Credit Card Information'

        elif self.html.find("Thank you for your order. Please wait") != -1:
            self.status = 'Processing'

        elif self.html.find("Thank you for your purchase!") != -1:
            self.status = 'Order ID Found'
            order_begin = self.html.find('Order #')
            self.order_id = self.html[order_begin+6:order_begin+12]

        elif self.html.find("Inventory issues") != -1:
            self.status = 'Item unavailable'

        else:
            self.status = 'No Errors'
        return self.status

    def load_phantom_cookies(self):
        se_cookies_login = []
        se_cookies_site = []
        se_cookies_shopify = []
        for cookie in self.session.cookies:
            dict = {'domain': cookie.domain,
                    'path': cookie.path,
                    'value': cookie.value,
                    'name': cookie.name}
            if cookie.domain == self.domain_site :
                se_cookies_site.append(dict)
            elif cookie.domain == self.domain_login :
                se_cookies_login.append(dict)
            elif cookie.domain == self.domain_shopify :
                se_cookies_shopify.append(dict)
        self.phantom.get('https://' + self.domain_login + '/account/login')
        for cookie in se_cookies_login:
            self.phantom.add_cookie(cookie)
        self.phantom.refresh()
        self.phantom.get('http://' + self.domain_site)
        for cookie in se_cookies_site:
            self.phantom.add_cookie(cookie)
        self.phantom.refresh()
        self.phantom.get('https://' + self.domain_shopify)
        for cookie in se_cookies_shopify:
            self.phantom.add_cookie(cookie)

    def open_manual_browser(self):
        '''
        copy requests session cookies
        use cookies to load to selenium browser at current domain
        :return: None
        '''
        se_cookies_login = []
        se_cookies_site = []
        se_cookies_shopify = []
        big_cookie = None
        for cookie in self.session.cookies:
            dict = {'domain': cookie.domain,
                    'path': cookie.path,
                    'value': cookie.value,
                    'name': cookie.name}
            if cookie.domain == self.domain_site :
                se_cookies_site.append(dict)
            elif cookie.domain == self.domain_login :
                se_cookies_login.append(dict)
            elif cookie.domain == self.domain_shopify :
                se_cookies_shopify.append(dict)
            if cookie.path != '/':
                big_cookie = dict
        self.firefox = webdriver.Firefox()
        self.firefox.get('https://' + self.domain_login + '/account/login')
        for cookie in se_cookies_login:
            self.firefox.add_cookie(cookie)
        self.firefox.refresh()
        self.firefox.get('http://' + self.domain_site)
        for cookie in se_cookies_site:
            self.firefox.add_cookie(cookie)
        self.firefox.refresh()
        self.firefox.get('https://' + self.domain_shopify)
        for cookie in se_cookies_shopify:
            self.firefox.add_cookie(cookie)
        self.firefox.get('https://' + self.domain_shopify + big_cookie['path'])

    def get_checkout_url(self):
        '''
        find checkout url from last received http response
        :return: None
        '''
        add_url = ''
        for cookie in self.session.cookies:
            if cookie.name == 'checkout':
                add_url = cookie.path
        url = 'https://' + self.domain_shopify + add_url
        self.checkout_url = url

    def save_html_tree(self, response):
        '''
        save tree and html from last response
        :param response: response text from http request
        :return:
        '''
        self.tree = html.fromstring(response)
        self.html = response

    def save_screenshot(self, name='default'):
        self.phantom.save_screenshot('shopify3/' + self.name +
                                     '/orders/{0}-{1}-{2}.png'.format(self.email[0:7], self.product_id, name))
