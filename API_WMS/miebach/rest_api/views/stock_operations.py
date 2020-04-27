from common import *


def reduce_stock(user, stocks=[], quantity=0, seller_id='', receipt_type='', receipt_number=1):
    for stock in stocks:
        if stock.quantity > quantity:
            stock.quantity -= quantity
            change_seller_stock(seller_id, stock, user, quantity, 'dec')
            save_sku_stats(user, stock.sku_id, receipt_number, receipt_type, -quantity, stock)
            quantity = 0
            if stock.quantity < 0:
                stock.quantity = 0
            stock.save()
        elif stock.quantity <= quantity:
            quantity -= stock.quantity
            change_seller_stock(seller_id, stock, user, stock.quantity, 'dec')
            save_sku_stats(user, stock.sku_id, receipt_number, receipt_type, -quantity, stock)
            stock.quantity = 0
            stock.save()
        if quantity == 0:
            break
    return True
