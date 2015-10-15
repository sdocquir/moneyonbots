__author__ = 'Selim Docquir'

import requests
import re, sys, time, traceback
from selenium import webdriver
import Tkinter as tk

class BigCartelBot(object):
    def __init__(self, product_id = None, product_index = None):
        self.title          = "BigCartel"
        self.product_names  = None
        self.stores         = None
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
        self.set_domain()

    def read_info_files(self):
        with open('bigcartel/text_files/product_name.txt', 'r') as f:
            skipped_instructions = False
            while skipped_instructions is False:
                position = f.tell()
                if not f.readline().startswith('#'):
                    skipped_instructions = True
                    f.seek(position)
            self.product_names = f.read().lower()

        with open('bigcartel/text_files/stores.txt', 'r') as f:
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

        def tk_exit(self):
            self.store = store.get()
            self.product_name = prod.get().lower().split()
            temp_id = id.get()
            if temp_id != '':
                self.product_id = temp_id
            root.destroy()

        tk.Label(root, text="Store").grid(row=0, column =0)
        tk.OptionMenu(root, store, *self.stores).grid(row=0, column=1)
        tk.Label(root,text='').grid(row=1)
        tk.Label(root, text="Product ID").grid(row=3, column=0)
        tk.Entry(root, textvariable=id).grid(row=3, column=1)
        tk.Label(root, text='OR').grid(row=4)
        tk.Label(root, text="Keywords").grid(row=5, column=0)
        tk.Entry(root, textvariable=prod).grid(row=5, column=1)
        tk.Label(root, text='').grid(row=6)
        tk.Button(root, text='Submit', command=lambda: tk_exit(self), ).grid(row=7, column=0)
        tk.Button(root, text='Quit', command=sys.exit).grid(row=7, column=1)
        root.mainloop()

    def full_purchase(self):
        if self.product_id is None:
            self.find_product_id()
        self.get_product_info()
        print 'Found product at ' + self.product_handle
        print 'ID : ', self.product_id
        print 'Index: ', self.product_index
        print "Waiting for product to be available"
        self.check_for_availability()
        print "Product is now available"
        self.add_to_cart(self.product_id)
        print "Add to cart request sent, verifying that cart holds product"
        if self.is_cart_added() is False:
            print "Product is not in cart, refreshing until added to cart"
            while self.is_cart_added() is False:
                self.add_to_cart(self.product_id)
                self.refresh_count += 1
                print "Refresh #", str(self.refresh_count) + "\r",
        print "Product is now in cart, opening browser"
        self.save_page('cart')
        self.open_browser()


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
                print '/Encountered error:/'
                print traceback.format_exc()
                print '/End Error/'
                print 'Continuing'
        self.refresh_count = 0


    def add_to_cart(self, product_id):
        item = {'cart[add][id]': '{0}'.format(product_id),
                'submit': ''}
        r = self.session.post(self.cart_url, data=item,)
        self.cart_cookie = r.cookies['_big_cartel_session']
        self.html = r.text

    def is_cart_added(self):
        if self.html.find('All others are either sold or being held') != -1:
            return False
        else:
            return True

    def save_page(self, description = 'default'):
        f = open('bigcartel/orders/{0}-{1}-{2}.html'.format(self.refresh_count, self.product_id, description), 'w')
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

    def open_browser(self):
        self.driver = webdriver.Firefox()
        self.driver.get(self.cart_url)
        cart_cookie = {'domain': self.domain,
                       'path': '/',
                       'value': self.cart_cookie,
                       'name':'_big_cartel_session',
                       'secure': False,
                       'expiry': None}
        self.driver.add_cookie(cart_cookie)
        self.driver.get(self.cart_url)


