ROLE_TYPE_CHOICES = (('supplier', 'Supplier'),)
UNIT_TYPE_CHOICES = (('quantity', 'Quantity'), ('amount', 'Amount'))
REMARK_CHOICES = (('Freight Charges Included', 'Freight Charges Included'),
                  ('Freight Charges Not Included', 'Freight Charges Not Included'), ('', ''))
TERMS_CHOICES = (('sales', 'Sales'),
                  ('purchases', 'Purchases'), ('', ''))
CUSTOMIZATION_TYPES = (('price_custom', 'Price Customization'), ('product_custom', 'Product Customization'),
                       ('price_product_custom', 'Price and Product Customization'))
CUSTOMER_ROLE_CHOICES = (('', ''), ('customer_user', 'User'), ('customer_hod', 'HOD'), ('customer_admin', 'Admin'))
APPROVAL_STATUSES = (('accept', 'Accept'), ('reject', 'Reject'), ('pending', 'Pending'))