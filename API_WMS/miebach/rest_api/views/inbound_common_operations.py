def generate_grn_pagination(sku_list):
    # header 220
    # footer 125
    # table header 44
    # row 46
    # total 1358
    # default 24 items
    # last page 21 items
    sku_len = len(sku_list)
    sku_list1 = []
    for index, sku in enumerate(sku_list):
        # sku += (index+1,)
        sku_list1.append(sku)
    sku_list = sku_list1
    t = sku_list[0]
    # for i in range(47): sku_list.append(t)#remove it
    sku_slices = [sku_list[i: i + 24] for i in range(0, len(sku_list), 24)]
    extra_tuple = ('', '', '', '', '', '', '', '', '', '', '', '')
    if len(sku_slices[-1]) == 24:
        temp = sku_slices[-1]
        sku_slices[-1] = temp[:23]
        temp = [temp[-1]]
        for i in range(20): temp.append(extra_tuple)
        sku_slices.append(temp)
    else:
        for i in range((21 - len(sku_slices[-1]))): sku_slices[-1].append(extra_tuple)
    return sku_slices