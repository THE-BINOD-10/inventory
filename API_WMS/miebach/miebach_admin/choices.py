ROLE_TYPE_CHOICES = (('supplier', 'Supplier'),)
UNIT_TYPE_CHOICES = (('quantity', 'Quantity'), ('amount', 'Amount'))
REMARK_CHOICES = (('Freight Charges Included', 'Freight Charges Included'),
                  ('Freight Charges Not Included', 'Freight Charges Not Included'), ('', ''),
                  ('Charges are Inclusive of Freight.', 'Charges are Inclusive of Freight.'),
                  ('Freight as applicable will be charged extra.', 'Freight as applicable will be charged extra.'),
                  )
TERMS_CHOICES = (('sales', 'Sales'),
                  ('purchases', 'Purchases'), ('', ''))
CUSTOMIZATION_TYPES = (('price_custom', 'Price Customization'),
                       ('price_product_custom', 'Price and Product Customization'))
CUSTOMER_ROLE_CHOICES = (('', ''), ('customer_user', 'user'), ('customer_hod', 'hod'), ('customer_admin', 'admin'))
APPROVAL_STATUSES = (('accept', 'Accept'), ('reject', 'Reject'), ('pending', 'Pending'))
SELLABLE_CHOICES = (('sellable', 'Sellable'), ('non_sellable', 'Non Sellable'))
