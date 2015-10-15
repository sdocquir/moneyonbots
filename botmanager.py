__author__ = 'Selim Docquir'

import Tkinter as tk
from functools import partial



from shopify2.utb import UTBBot
from shopify2.bottleneck import BottleneckBot

from shopify3.mondo import MondoBot
from shopify3.obey import ObeyBot
from shopify3.pt import PTBot
from shopify3.thevacvvm import TheVacvvmBot
from shopify3.invisibleindustries import InvisibleIndustriesBot
from shopify3.commonwealth import CommonWealthBot
from shopify3.zendragon import ZenDragonBot
from shopify3.extrabutter import ExtraButterBot
from shopify3.dhm import DHMBot
from shopify3.jameseads import JamesEadsBot
from shopify3.amesbros import AmesbrosBot
from shopify3.spusta import SpustaBot
from shopify3.hcg import HcgBot
from shopify3.selim import SelimBot

from paypal.paypal import PaypalBot
from bigcartel.bigcartel import BigCartelBot
from bigcartel2.bigcartel2 import BigCartel2Bot



bots = ['Mondo', 'DHM', 'Galerie F', 'UTB', 'Bottleneck',
        'Obey', 'P&T', 'James Eads', 'AmesBros', 'Spusta', 'HCG',
        'Selim',
        'Invisible Industries', 'The Vacvvm', 'ZenDragon',
        'CommonWealth', 'ExtraButter',
        'BigCartel', 'BigCartel 2', 'Paypal']


def main():
    root = tk.Tk()
    root.wm_title("PosterBot")
    row = 0
    column = 0
    for txt in bots:
        if column < 4:
            but = tk.Button(root, text=txt,padx=30,pady=10, command=partial(tk_exit, txt, root))
            but.grid(row=row, column = column, sticky= tk.W+tk.E+tk.S+tk.N)
            column += 1
        else:
            row += 1
            column = 0
            but = tk.Button(root, text=txt,padx=30,pady=10, command=partial(tk_exit, txt, root))
            but.grid(row=row, column = column, sticky= tk.W+tk.E+tk.S+tk.N)
            column += 1

    root.mainloop()
    input()

def tk_exit(value, root):
    root.destroy()
    print value
    bot = None
    if value == 'Mondo':
        bot = MondoBot()
    elif value == 'DHM':
        bot = DHMBot()
    elif value == 'UTB':
        bot = UTBBot()
    elif value == 'Bottleneck':
        bot = BottleneckBot()
    elif value == 'Obey':
        bot = ObeyBot()
    elif value == 'P&T':
        bot = PTBot()
    elif value == 'James Eads':
        bot = JamesEadsBot()
    elif value == 'AmesBros':
        bot = AmesbrosBot()
    elif value == 'Spusta':
        bot = SpustaBot()
    elif value == 'HCG':
        bot = HcgBot()
    elif value == 'Selim':
        bot = SelimBot()
    elif value == 'Invisible Industries':
        bot = InvisibleIndustriesBot()
    elif value == 'The Vacvvm':
        bot = TheVacvvmBot()
    elif value == 'ZenDragon':
        bot = ZenDragonBot()
    elif value == 'CommonWealth':
        bot = CommonWealthBot()
    elif value == 'ExtraButter':
        bot = ExtraButterBot()
    elif value == 'Paypal':
        bot = PaypalBot()
    elif value == 'BigCartel':
        bot = BigCartelBot()
    elif value == 'BigCartel 2':
        bot = BigCartel2Bot()

    bot.full_purchase()

if __name__ == "__main__":
    main()