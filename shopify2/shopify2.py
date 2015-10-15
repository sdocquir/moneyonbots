__author__ = 'Selim Docquir'

import requests
import sys, traceback
import re
import arrow
import time
import Tkinter as tk
from lxml import html
from selenium import webdriver

# Defining options for the GUI
modes = [('Gift Card', 1), ('Credit Card', 2), ('Paypal', 3)]
editions = [('Regular', 1), ('Variant', 2)]
product_types = [('All Products', 1), ('Vinyl', 2)]
shipping = [('Shipping', 1), ('No shipping', 2)]
# Defining regex for finding correct edition
regular = "^((?!variant).)*$"
variant = ".*variant.*"


class ShopifyV2Bot(object):
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
        self.gateway        = ''
        self.gateway_cc     = ''
        self.gateway_pp     = ''
        self.domain_site    = ''
        self.domain_login   = ''
        self.domain_shopify = ''
        self.list_accounts  = []
        self.list_info      = []
        self.cc_info_raw    = []
        self.product_names  = None
        self.session        = requests.Session()
        self.driver         = None                  # will be used for selenium browser if needed
        self.status         = 'Initializing'
        self.cc_info        = []                    # list of cc info from user input
        self.cc_address     = []                    # list of cc address from user input
        self.gift_cards     = []
        self.product_id     = None
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
        self.refresh_count  = 0                     # keeps track of how many refreshes has been done
        self.delay          = 0                     # delays in seconds between applying credit card charges
        self.attempts       = 1                     # count of checkout attempted
        self.mode           = 1
        self.product_type   = 1                     # set modes to default 1
        self.edition_choice = 1
        self.shipping       = 1
        self.mode_human     = None
        self.edition_choice_human = None            # holds human readable choices for outputting to console



    def analyze_input(self):
        if self.edition_choice == 1:                # set correct regex based on user input
            self.edition_choice_human = "Regular"
            self.edition_choice = "^((?!variant).)*$"
        elif self.edition_choice == 2:
            self.edition_choice_human = "Variant"
            self.edition_choice = ".*variant.*"

        if self.mode == 1:
            self.mode_human = "Gift Card"
        elif self.mode == 2:
            self.mode_human = "Credit Card"
            self.input_cc_info()                    # ask user for cc info if payment method is cc

        for sublist in self.list_info:                   # initialize password and gift cards based on selected account
            if sublist[0] == self.email:
                self.password = sublist[1]
                for x in range(2, len(sublist)):
                    self.gift_cards.append(sublist[x])

    def print_info(self):
        print "Email:           ", self.email
        print "Product:         ", self.product_name
        print "Edition:         ", self.edition_choice_human
        print "Mode:            ", self.mode_human
        print "Delay:           ", self.delay, 'seconds'
        if self.mode == 1:
            for gc in self.gift_cards:
                print "Code:            ", "****"+gc[-4:]
        elif self.mode == 2:
            print "CC:              ", "****"+self.cc_info[2][-4:]

    def read_info_files(self):
        # open all txt file needed, skip instructions and save content
        with open('shopify2/' + self.name +'/text_files/account_info.txt', 'r') as f:
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

        with open('shopify2/' + self.name + '/text_files/cc_info.txt', 'r') as f:
            skipped_instructions = False
            while skipped_instructions is False:
                position = f.tell()
                if not f.readline().startswith('#'):
                    skipped_instructions = True
                    f.seek(position)
            self.cc_info_raw = f.read().splitlines()

        with open('shopify2/' + self.name + '/text_files/product_name.txt', 'r') as f:
            skipped_instructions = False
            while skipped_instructions is False:
                position = f.tell()
                if not f.readline().startswith('#'):
                    skipped_instructions = True
                    f.seek(position)
            self.product_names = f.read().lower()

    def set_domain(self):
        self.title = self.name.capitalize() + ' Bot'
        self.products_url = 'http://' + self.domain_site + '/products.json'
        self.site_url = 'http://' + self.domain_site
        self.cart_url = self.site_url + "/cart"
        self.cart_add_url = self.site_url + "/cart/add"
        self.read_info_files()
        self.product_name   = self.product_names.split() # list of keywords to look for
        self.input_info()                           # call GUI
        self.analyze_input()
        self.print_info()


    def full_purchase(self):
        try:
            if self.mode == 3:
                self.pp_login()
            self.login()
            self.find_product_id()
            print 'Product ID is #               ', self.product_id
            print 'Product Handle is             ', self.product_handle
            print 'Found product at              ', arrow.now().time()
            self.add_to_cart(self.product_id)
            print 'Product in cart at            ', arrow.now().time()
            self.rep_start_checkout()
            print 'Product available at          ', arrow.now().time()
            self.checkout1()
            self.checkout2()
            while self.check_status() == 'Shipping Method Error' and self.attempts <= 5:
                print "Attempt #" + str(self.attempts)
                self.attempts += 1
                self.checkout2()
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
                self.open_browser()
        except:
            print 'Error:'
            print traceback.format_exc()
            print 'End Error/'
            self.open_browser()
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
            self.product_name = prod.get().lower().split()
            temp_id = id.get()
            if temp_id != '':
                self.product_id = temp_id
            self.delay = int(delay.get())
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
            self.delay = delay_seconds.get()
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
        delay_seconds.set(self.delay)
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
        print url
        # url = 'https://' + self.domain_login + '/account/login'
        login = {'form_type': 'customer_login',
                 'customer[email]': '{0}'.format(self.email),
                 'customer[password]': '{0}'.format(self.password)}
        r = self.session.post(url[0], data=login)
        self.save_html_tree(r.text)

    def pp_login(self):
        '''
        login to paypal to facilitate checkout step
        :return: None
        '''
        headers = {'User-Agent': 'Chrome/43.0.2357.81'}
        r = self.session.get('https://paypal.com/signin', headers=headers)
        self.save_html_tree(r.text)
        csrf = self.tree.xpath('//input[@name="_csrf"]/@value')[0]
        locale = self.tree.xpath('//input[@name="locale.x"]/@value')[0]
        process = self.tree.xpath('//input[@name="processSignin"]/@value')[0]

        print csrf, locale, process
        # bp_mid = self.tree.xpath('//input[@name="bp_mid"]/@value')[0]
        # flow_name = self.tree.xpath('//input[@name="flow_name"]/@value')[0]
        # fso = self.tree.xpath('//input[@name="fso"]/@value')
        login_email = 'selimdocquir@gmail.com'
        login_password = 'Ulb25826?!+'
        login = {'_csrf' : csrf,
                 'locale.x' : locale,
                 'processSignin' : process,
                # 'fso' : fso,
                # 'bp_mid' : bp_mid,
                # 'flow_name' : flow_name,
                'login_email' : login_email,
                'login_password' : login_password}
        url = 'https://paypal.com/signin'
        r = self.session.post(url, data=login, headers=headers)
        print r.text
        exit(1)
    def find_product_id(self):
        '''
        call correct function based on user input
        :return:
        '''
        if self.product_type == 1:
            self.find_product_id_all()
        elif self.product_type == 2:
            self.find_product_id_vinyl()

    def find_product_id_all(self):
        '''
        refresh products page, parse json and look for product
        change product_id when found
        :return: None
        '''
        while self.product_id is None:
            r = self.session.get(self.products_url)
            json_data = r.json()
            for i in range(len(json_data['products'])):
                product_handles = json_data['products'][i]['handle']
                product_titles  = json_data['products'][i]['title']
                if (len(self.product_name) > 0 and
                        re.search(self.product_name[0], product_handles, re.IGNORECASE) and
                        (re.search(self.edition_choice, product_handles, re.IGNORECASE) or
                         re.search(self.edition_choice, product_titles, re.IGNORECASE))):
                    self.product_id = json_data['products'][i]['variants'][0]['id']
                    self.product_index = i
                    self.product_handle = product_handles

                if (len(self.product_name) > 1 and
                        re.search(self.product_name[1], product_handles, re.IGNORECASE) and
                        (re.search(self.edition_choice, product_handles, re.IGNORECASE) or
                         re.search(self.edition_choice, product_titles, re.IGNORECASE))):
                    self.product_id = json_data['products'][i]['variants'][0]['id']
                    self.product_index = i
                    self.product_handle = product_handles

                if (len(self.product_name) > 2 and
                        re.search(self.product_name[2], product_handles, re.IGNORECASE) and
                        (re.search(self.edition_choice, product_handles, re.IGNORECASE) or
                         re.search(self.edition_choice, product_titles, re.IGNORECASE))):
                    self.product_id = json_data['products'][i]['variants'][0]['id']
                    self.product_index = i
                    self.product_handle = product_handles
            self.refresh_count += 1
            print "Refresh #", str(self.refresh_count) + '\r',
        self.product_id = str(self.product_id)

    def find_product_id_vinyl(self):
        '''
        refresh products page, parse json and look for product
        change product_id when found
        extra : checks for product type == 'Vinyl'
        :return: None
        '''
        while self.product_id is None:
            r = self.session.get(self.products_url)
            json_data = r.json()
            for i in range(len(json_data['products'])):
                product_handles = json_data['products'][i]['handle']
                product_titles  = json_data['products'][i]['title']
                product_types   = json_data['products'][i]['product_type']
                if (len(self.product_name) > 0 and
                        product_types == 'Vinyl' and
                        re.search(self.product_name[0], product_handles, re.IGNORECASE) and
                        (re.search(self.edition_choice, product_handles, re.IGNORECASE) or
                         re.search(self.edition_choice, product_titles, re.IGNORECASE))):
                    self.product_id = json_data['products'][i]['variants'][0]['id']
                    self.product_index = i
                    self.product_handle = product_handles

                if (len(self.product_name) > 1 and
                        product_types == 'Vinyl' and
                        re.search(self.product_name[1], product_handles, re.IGNORECASE) and
                        (re.search(self.edition_choice, product_handles, re.IGNORECASE) or
                         re.search(self.edition_choice, product_titles, re.IGNORECASE))):
                    self.product_id = json_data['products'][i]['variants'][0]['id']
                    self.product_index = i
                    self.product_handle = product_handles

                if (len(self.product_name) > 2 and
                        product_types == 'Vinyl' and
                        re.search(self.product_name[2], product_handles, re.IGNORECASE) and
                        (re.search(self.edition_choice, product_handles, re.IGNORECASE) or
                         re.search(self.edition_choice, product_titles, re.IGNORECASE))):
                    self.product_id = json_data['products'][i]['variants'][0]['id']
                    self.product_index = i
                    self.product_handle = product_handles
            self.refresh_count += 1
            print "Refresh #", str(self.refresh_count) + '\r',
        print
        self.refresh_count = 0
        self.product_id = str(self.product_id)

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
        self.address_id = self.tree.xpath('//select[@id="checkout_shipping_address_id"]/option[@selected="selected"]/@data-properties')
        address_data = {}
        for pair in self.address_id[0].replace('"', '').strip('{}"').split(','):
            k, v = pair.split(':')
            address_data[k] = v
        base_data = {'authenticity_token': self.authenticity,
                     'commit': 'Continue',
                     'previous_step': 'contact_information',
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

    def checkout2(self):
        '''
         find payment gateways
         call correct checkout2 function based on user payment method
         if GC : apply gift cards and call checkout2_gift
         If CC : apply delay and call checkout2_cc
        :return:None
        '''
        gateways = self.tree.xpath('//div/@data-select-gateway')
        if len(gateways) > 0:
            self.gateway_cc = gateways[0]
        if len(gateways) > 1:
            self.gateway_pp = gateways[1]

        if self.mode == 1:
            for gc in self.gift_cards:
                self.apply_gift(gc)
                print 'Applied GC', gc
            self.gift_cards = []
            time.sleep(self.delay)
            self.checkout2_gift()
        elif self.mode == 2:
            if self.delay > 0:
                print "Delaying checkout by " + str(self.delay)
                time.sleep(self.delay)
                self.delay = 0
            self.checkout2_cc()

    def checkout2_gift(self):
        '''
        send POST request to payment url with free as payment gateway, and same billing address
        :return: None
        '''
        c = self.tree.xpath('//input[@name="c"]/@value')
        d = self.tree.xpath('//input[@name="d"]/@value')
        #find shipping rate.
        #if not found, put empty string to pass to dict for post request
        shipping_rate = self.tree.xpath('//input[@name="checkout[shipping_rate_id]"]/@value')
        if len(shipping_rate) < 1:
            shipping_rate.append('')
        # find payment url by searching for string sessions in href
        # can be either west or east shopify
        payment_url = ''
        urls = self.tree.xpath('//form/@action')
        for url in urls:
            if 'sessions' in url:
                payment_url = url
        data = {'authenticity_token': self.authenticity,
                'c': c[0],
                'd': d[0],
                'checkout[payment_gateway]': 'free',
                'checkout[different_billing_address': 'false',
                'checkout[buyer_accepts_marketing]':'0',
                'checkout[client_details][browser_width]': '1583',
                'checkout[client_details][browser_height]': '799',
                'complete': 'Place my order'}
        if self.shipping == 1:
            data.update({'checkout[shipping_rate_id]': shipping_rate[0]})
        r = self.session.post(payment_url, data=data)
        self.save_html_tree(r.text)

    def checkout2_cc(self):
        '''
        send POST request to payment url using cc payment gateway and supplied user billing address
        :return: None
        '''
        c = self.tree.xpath('//input[@name="c"]/@value')
        d = self.tree.xpath('//input[@name="d"]/@value')
        shipping_rate = self.tree.xpath('//input[@name="checkout[shipping_rate_id]"]/@value')
        if shipping_rate == []:
            shipping_rate.append('')
        payment_url = ''
        urls = self.tree.xpath('//form/@action')
        for url in urls:
            if 'sessions' in url:
                payment_url = url
        data = {'authenticity_token': self.authenticity,
                'c': c[0],
                'd': d[0],
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
                'checkout[client_details][browser_height]': '799',
                'complete': 'Place my order'}
        if self.shipping == 1:
            data.update({'checkout[shipping_rate_id]': shipping_rate[0]})
        r = self.session.post(payment_url, data=data)
        self.save_html_tree(r.text)

    def checkout_2_pp(self):
        '''
        send POST request to payment url using pp payment gateway
        :return: None
        '''
        c = self.tree.xpath('//input[@name="c"]/@value')
        d = self.tree.xpath('//input[@name="d"]/@value')
        shipping_rate = self.tree.xpath('//input[@name="checkout[shipping_rate_id]"]/@value')
        if shipping_rate == []:
            shipping_rate.append('')
        # find payment url by searching for string sessions in href
        # can be either west or east shopify
        payment_url = ''
        urls = self.tree.xpath('//form/@action')
        for url in urls:
            if 'sessions' in url:
                payment_url = url
        data = {'authenticity_token': self.authenticity,
                'c': c[0],
                'd': d[0],
                'checkout[payment_gateway]': self.gateway_pp,
                'checkout[different_billing_address': 'false',
                'checkout[buyer_accepts_marketing]':'0',
                'checkout[client_details][browser_width]': '1583',
                'checkout[client_details][browser_height]': '799',
                'complete': 'Place my order'}
        if self.shipping == 1:
            data.update({'checkout[shipping_rate_id]': shipping_rate[0]})
        r = self.session.post(payment_url, data=data)
        self.save_html_tree(r.text)

    def load_order_page(self):
        '''
        send GET request to checkout_url.
        used when order is successful
        :return: None
        '''
        r = self.session.get(self.checkout_url)
        self.save_html_tree(r.text)

    def save_page(self, description = 'default'):
        '''
        save file in orders folder using email and checkout url
        :param description: string code for what kind of file needs to be saved
        :return:
        '''
        f = open('shopify2/' + self.name + '/orders/{0}-{1}-{2}.html'.format(self.email[0:7], self.product_id[-4:], description), 'w')
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

    def open_browser(self):
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
        self.driver = webdriver.Firefox()
        self.driver.get('https://' + self.domain_login + '/account/login')
        for cookie in se_cookies_login:
            self.driver.add_cookie(cookie)
        self.driver.refresh()
        self.driver.get('http://' + self.domain_site)
        for cookie in se_cookies_site:
            self.driver.add_cookie(cookie)
        self.driver.refresh()
        self.driver.get('https://' + self.domain_shopify)
        for cookie in se_cookies_shopify:
            self.driver.add_cookie(cookie)
        self.driver.get('https://' + self.domain_shopify + big_cookie['path'])

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
