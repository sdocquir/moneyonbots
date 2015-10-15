__author__ = 'Selim Docquir'

import requests
import re, sys, time
from lxml import html
from selenium import webdriver
import Tkinter as tk

options = [('Buy first', 1), ('Buy last', 2), ('Buy all', 3)]

class BigCartel2Bot(object):
    def __init__(self, product_id = None, product_index = None):
        self.title          = "BigCartel"
        self.product_names  = None
        self.stores         = None
        self.option         = None
        self.email          = ''
        self.password       = ''
        self.address        = []
        self.read_info_files()
        self.store          = ''
        self.products_url   = ''
        self.cart_url       = ''
        self.domain         = ''
        self.session        = requests.Session()
        self.driver         = None
        self.status         = 'Initializing'
        self.refresh_count  = 0
        self.product_name   = self.product_names.split()
        self.product_id     = product_id
        self.available      = False
        self.product_index  = product_index
        self.product_handle = ''
        self.cart_cookie    = None
        self.input_info()
        self.input_address_info()
        self.set_domain()

    def read_info_files(self):
        with open('bigcartel2/text_files/product_name.txt', 'r') as f:
            skipped_instructions = False
            while skipped_instructions is False:
                position = f.tell()
                if not f.readline().startswith('#'):
                    skipped_instructions = True
                    f.seek(position)
            self.product_names = f.read().lower()

        with open('bigcartel2/text_files/stores.txt', 'r') as f:
            skipped_instructions = False
            while skipped_instructions is False:
                position = f.tell()
                if not f.readline().startswith('#'):
                    skipped_instructions = True
                    f.seek(position)
            self.stores = f.read().splitlines()

    def input_info(self):
        root = tk.Tk()
        root.wm_title(self.title)
        store = tk.StringVar()
        store.set(self.stores[0])
        prod = tk.StringVar()
        prod.set(self.product_names)
        id = tk.StringVar()
        id.set('')
        # opt = tk.IntVar()
        # opt.set(1)

        def tk_exit(self):
            self.store = store.get()
            self.product_name = prod.get().lower().split()
            temp_id = id.get()
            # self.option = opt.get()
            if temp_id != '':
                self.product_id = temp_id

            root.destroy()

        # for txt, val in options:
        #     tk.Radiobutton(root, text=txt, padx=20, variable=opt,
        #                    command=opt.get(), value=val).grid(row=6, column = val)
        tk.Label(root, text="Store").grid(row=0, column =1)
        tk.OptionMenu(root, store, *self.stores).grid(row=0, column=2)
        tk.Label(root,text='').grid(row=1)
        tk.Label(root, text="Product ID").grid(row=3, column=1)
        tk.Entry(root, textvariable=id).grid(row=3, column=2)
        tk.Label(root, text='OR').grid(row=4, column=1)
        tk.Label(root, text="Keywords").grid(row=5, column=1)
        tk.Entry(root, textvariable=prod).grid(row=5, column=2)
        tk.Label(root, text='').grid(row=6)

        tk.Button(root, text='Submit', command=lambda: tk_exit(self), ).grid(row=7, column=1)
        tk.Button(root, text='Quit', command=sys.exit).grid(row=7, column=2)
        root.mainloop()

    def full_purchase(self):
        if self.product_id is None:
            self.find_product_id()
        self.get_product_info()
        print 'Email :', self.email
        print 'Password: ', self.password
        print 'Address: ', self.address
        print 'Found product at ' + self.product_handle
        print 'ID : ', self.product_id
        print 'Index: ', self.product_index
        print "Waiting for product to be available"
        self.check_for_availability()
        print "Product is now available"
        self.add_to_cart(self.product_id)
        print "Product added to cart, verifying that cart holds product"
        if self.is_cart_added() is False:
            print "Product is not in cart, refreshing until added to cart"
            while self.is_cart_added() is False:
                self.add_to_cart(self.product_id)
                self.refresh_count += 1
                print "Refresh #", str(self.refresh_count) + "\r",
        self.save_page('cart')
        print "Product is in cart, starting checkout"

        self.start_checkout()
        self.save_page('first-checkout')
        print "Reached checkout step"

        self.patch_checkout()
        self.save_page('patch-checkout')
        print "Reached end of checkout step"

        self.express_checkout()
        self.save_page('express-checkout')
        self.paypal_checkout_page()
        self.save_page('paypal-checkout')
        print "Reached Paypal Step 1"

        self.paypal_checkout_step1()
        self.save_page('paypal-1')
        print "Reached Paypal Step 2"
        self.paypal_checkout_step2()
        self.save_page('paypal-2')
        print "Finished Paypal Checkout"
        self.paypal_confirmation()


    def start_checkout(self):
        checkout = {'checkout': '1'}
        r = self.session.post(self.cart_url,data=checkout)
        self.html = r.text
        self.checkout_url = r.url
        self.cart_number = r.url[-25:]
        self.api_checkout_url = 'https://api.bigcartel.com/store/{0}/carts/{1}'.format(self.store_id, self.cart_number)

    def patch_checkout(self):
        patch_data = {'buyer_email': self.email,
                'buyer_first_name': self.address[0],
                'buyer_last_name': self.address[1],
                'shipping_address_1': self.address[2],
                'shipping_address_2': self.address[3],
                'shipping_city': self.address[4],
                'shipping_country_id': '43',
                'shipping_state': self.address[5],
                'shipping_zip': self.address[6],
                'note': '',
                }
        r = self.session.patch(self.api_checkout_url, data=patch_data)
        r = self.session.get(self.checkout_url)
        self.html = r.text

    def express_checkout(self):
        r = self.session.get(self.api_checkout_url+'/express_checkouts/new')
        self.html = r.text
        self.paypal_url = r.json()['location']
        self.paypal_url += '&force_sa=true'
        print self.paypal_url

    def paypal_checkout_page(self):
        r = self.session.get(self.paypal_url)
        self.html = r.text
        self.tree = html.fromstring(r.text)



    def paypal_checkout_step1(self):
        url = self.tree.xpath('//form[@id="parentForm"]/@action')
        auth = self.tree.xpath('//form[@id="parentForm"]/input[@name="auth"]/@value')
        SESSION = self.tree.xpath('//input[@id="pageSession"]/@value')
        dispatch = self.tree.xpath('//input[@name="dispatch"]/@value')
        CONTEXT = self.tree.xpath('//input[@name="CONTEXT"]/@value')
        currentSession = self.tree.xpath('//input[@name="currentSession"]/@value')
        currentDispatch = self.tree.xpath('//input[@name="currentDispatch"]/@value')
        data = {'login_email': self.email,
                'login_password': self.password,
                'auth': auth[0],
                'SESSION': SESSION[0],
                'dispatch': dispatch[0],
                'CONTEXT': CONTEXT[0],
                'currentSession':currentSession[0],
                'currentDispatch': currentDispatch[0],
                'login.x': 'Log In',
                'cmd': '_flow',
                'reviewPgReturn': '1',
                'pageState': 'login',
                'email_recovery': 'false',
                'password_recovery': 'false',
                'close_external_flow': 'false',
                'external_close_account_payment_flow': 'payment_flow',
                'pageServerName': 'merchantpaymentweb',
                'flow_name': 'xpt/Checkout/wps/Login'
                }
        r = self.session.post(url[0], data=data)
        self.html = r.text
        self.tree = html.fromstring(r.text)

    def paypal_checkout_step2(self):
        url = self.tree.xpath('//form[@method="post"]/@action')
        auth = self.tree.xpath('//form[@method="post"]/input[@name="auth"]/@value')
        SESSION = self.tree.xpath('//input[@name="SESSION"]/@value')
        dispatch = self.tree.xpath('//input[@name="dispatch"]/@value')
        CONTEXT = self.tree.xpath('//input[@name="CONTEXT"]/@value')
        currentSession = self.tree.xpath('//input[@name="currentSession"]/@value')
        currentDispatch = self.tree.xpath('//input[@name="currentDispatch"]/@value')
        data = {
                'auth': auth[0],
                'SESSION': SESSION[0],
                'dispatch': dispatch[0],
                'CONTEXT': CONTEXT[0],
                'currentSession':currentSession[0],
                'currentDispatch': currentDispatch[0],
                'continue': 'Pay Now',
                'cmd': '_flow',
                'reviewPgReturn': '1',
                'pageState': 'review',
                'close_external_flow': 'false',
                'external_close_account_payment_flow': 'payment_flow',
                'pageServerName':'merchantpaymentweb',
                }
        r = self.session.post(url[0], data=data)
        self.html = r.text
        self.tree = html.fromstring(r.text)

    def paypal_confirmation(self):
        if self.html.find('order has been received') != -1:
            print "Order succesful"
            order_number_begin = self.html.find('Order #')
            self.order_id = self.html[order_number_begin+6:order_number_begin+18]
            print "Order", self.order_id

    def find_product_id(self):
        while self.product_id is None:
            r = self.session.get(self.products_url)
            json_data = r.json()
            for i in range(len(json_data)):
                product_handles = json_data[i]['permalink']
                if (len(self.product_name) > 0 and
                        re.search(self.product_name[0], product_handles, re.IGNORECASE)):
                    self.product_id = json_data[i]['options'][0]['id']
                    self.product_handle = json_data[i]['permalink']
                    self.product_index = i

                if (len(self.product_name) > 1 and
                        re.search(self.product_name[1], product_handles, re.IGNORECASE)):
                    self.product_id = json_data['products'][i]['variants'][0]['id']
                    self.product_handle = json_data[i]['permalink']
                    self.product_index = i

                if (len(self.product_name) > 2 and
                        re.search(self.product_name[2], product_handles, re.IGNORECASE)):
                    self.product_id = json_data['products'][i]['variants'][0]['id']
                    self.product_handle = json_data[i]['permalink']
                    self.product_index = i
            self.refresh_count += 1
            print "Refresh #", str(self.refresh_count) + "\r",
        print
        self.refresh_count = 0
        self.product_id = str(self.product_id)

    def get_product_info(self):
        r = self.session.get(self.products_url)
        json_data = r.json()
        for i in range(len(json_data)):
            for j in range(len(json_data[i]['options'])):
                products_ids = json_data[i]['options'][j]['id']
                if str(self.product_id) == str(products_ids):
                    self.product_handle = json_data[i]['permalink']
                    self.product_index = i


    def check_for_availability(self):
        while self.available == False:
            try:
                time.sleep(0.2)
                r = self.session.get(self.products_url)
                json_data = r.json()
                if json_data[self.product_index]['status'] == 'active':
                    self.available = True
                else:
                    print "Refresh #", str(self.refresh_count) + "\r",
                    self.refresh_count += 1
            except:
                print 'Encountered error, continuing'
        self.refresh_count = 0


    def add_to_cart(self, product_id):
        item = {'cart[add][id]': '{0}'.format(product_id),
                'submit': ''}
        r = self.session.post(self.cart_url, data=item,)
        self.html = r.text

    def is_cart_added(self):
        if self.html.find('All others are either sold or being held') != -1:
            return False
        else:
            return True

    def save_page(self, description = 'default'):
        f = open('bigcartel2/orders/{0}-{1}-{2}.html'.format(self.email[:5], self.product_id, description), 'w')
        f.write(self.html.encode('UTF-8'))
        f.close()

    def set_domain(self):
        base_api_url     = 'http://api.bigcartel.com/{0}/'.format(self.store)
        store_api_url    = base_api_url + 'store.json'
        products_api_url = base_api_url + 'products.json?limit=5'
        r = requests.get(store_api_url)
        self.products_url   = products_api_url
        self.cart_url       = r.json()['url'] + '/cart'
        self.domain         = r.json()['url'][7:]
        self.store_id       = r.json()['id']

    def input_address_info(self):
        '''
        GUI for CC info
        set local variables to to value taken from cc_info.txt
        exit : exit program
        submit: save local variables to instances variables.
        :return:
        '''
        root = tk.Tk()

        def tk_exit(self):
            self.email = email.get()
            self.password = password.get()
            self.address = [fname.get(), lname.get(),add1.get(), add2.get(), city.get(), state.get(), zipcode.get()]
            root.destroy()

        tk.Label(root, text="First Name").grid(column=0)
        tk.Label(root, text="Last Name").grid(column=0)
        tk.Label(root, text="Address 1").grid(column=0)
        tk.Label(root, text="Address 2").grid(column=0)
        tk.Label(root, text="City").grid(column=0)
        tk.Label(root, text="State").grid(column=0)
        tk.Label(root, text="Zip Code").grid(column=0)
        tk.Label(root, text="PP-Email").grid(column=0)
        tk.Label(root, text="PP-Password").grid(column=0)
        fname = tk.StringVar()
        lname = tk.StringVar()
        add1 = tk.StringVar()
        add2 = tk.StringVar()
        city = tk.StringVar()
        state = tk.StringVar()
        zipcode = tk.StringVar()
        email = tk.StringVar()
        password = tk.StringVar()
        tk.Entry(root, textvariable=fname).grid(column=1, row=0)
        tk.Entry(root, textvariable=lname).grid(column=1, row=1)
        tk.Entry(root, textvariable=add1).grid(column=1, row=2)
        tk.Entry(root, textvariable=add2).grid(column=1, row=3)
        tk.Entry(root, textvariable=city).grid(column=1, row=4)
        tk.Entry(root, textvariable=state).grid(column=1, row=5)
        tk.Entry(root, textvariable=zipcode).grid(column=1, row=6)
        tk.Entry(root, textvariable=email).grid(column=1, row=7)
        tk.Entry(root, textvariable=password).grid(column=1, row=8)
        tk.Button(root, text='Submit', command=lambda: tk_exit(self), ).grid(row=15, column=0)
        tk.Button(root, text='Quit', command=sys.exit).grid(row=15, column=1)
        root.mainloop()
