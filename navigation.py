# one place that knows how to open every page
# the page modules are imported inside the function so we don't get circular imports

def go_to(page, root, current_user, go_home):
    if page == "dashboard":
        go_home()
    elif page == "products":
        from products import show_products
        show_products(root, current_user, go_home)
    elif page == "customers":
        from customers import show_customers
        show_customers(root, current_user, go_home)
    elif page == "billing":
        from billing import show_billing
        show_billing(root, current_user, go_home)
    elif page == "reports":
        from reports import show_reports
        show_reports(root, current_user, go_home)
    elif page == "categories":
        from categories import show_categories
        show_categories(root, current_user, go_home)
    elif page == "purchases":
        from purchases import show_purchases
        show_purchases(root, current_user, go_home)
    elif page == "settings":
        from settings import show_settings
        show_settings(root, current_user, go_home)
    elif page == "suppliers":
        from suppliers import show_suppliers
        show_suppliers(root, current_user, go_home)
