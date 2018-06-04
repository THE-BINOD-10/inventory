ROLE_TYPE_CHOICES = (('supplier', 'Supplier'),)
UNIT_TYPE_CHOICES = (('quantity', 'Quantity'), ('amount', 'Amount'))
REMARK_CHOICES = (('Freight Charges Included', 'Freight Charges Included'),
                  ('Freight Charges Not Included', 'Freight Charges Not Included'), ('', ''),
                  ('Charges are Inclusive of Freight.', 'Charges are Inclusive of Freight.'),
                  ('Freight as applicable will be charged extra.', 'Freight as applicable will be charged extra.'),
                  )
TERMS_CHOICES = (('sales', 'Sales'),
                  ('purchases', 'Purchases'), ('', ''))
CUSTOMIZATION_TYPES = (('price_custom', 'Price Customization'), ('product_custom', 'Product Customization'),
                       ('price_product_custom', 'Price and Product Customization'))
