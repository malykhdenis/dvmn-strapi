from io import BytesIO
import os

import requests
# from dotenv import load_dotenv

# load_dotenv()

STRAPI_API_URL = os.getenv('STRAPI_API_URL')
AUTH_HEADER = {'Authorization': f'bearer {os.getenv("STRAPI_TOKEN")}', }


def get_products():
    products = requests.get(
        os.path.join(STRAPI_API_URL, 'products'),
        headers=AUTH_HEADER,
    )
    products.raise_for_status()
    return products.json()


def get_product_with_picture(product_id):
    payload = {'populate': 'picture'}
    product = requests.get(
        os.path.join(STRAPI_API_URL, 'products', product_id),
        headers=AUTH_HEADER,
        params=payload,
    )
    product.raise_for_status()
    return product.json()


def download_picture(picture_url):
    picture_url = os.path.join(STRAPI_API_URL[:-4], picture_url,)
    picture_response = requests.get(picture_url)
    picture_response.raise_for_status()
    return BytesIO(picture_response.content)


def get_cart(telegram_id):
    cart_filter = {
            'filters[tg_id][$eq]': telegram_id,
            'populate[cartproducts][populate]': 'product',
        }
    user_cart = requests.get(
        os.path.join(STRAPI_API_URL, 'carts'),
        headers=AUTH_HEADER,
        params=cart_filter,
    )
    user_cart.raise_for_status()
    return user_cart.json()


def create_cart(telegram_id):
    cart_payload = {
        'data': {'tg_id': telegram_id},
    }
    create_cart = requests.post(
        os.path.join(STRAPI_API_URL, 'carts'),
        headers=AUTH_HEADER,
        json=cart_payload,
    )
    create_cart.raise_for_status()


def add_product(cart_id, product_id, amount):
    productcart_payload = {
        'data': {
            'cart': cart_id,
            'product': product_id,
            'amount': amount,
        }
    }
    add_product = requests.post(
        os.path.join(STRAPI_API_URL, 'product-in-carts'),
        headers=AUTH_HEADER,
        json=productcart_payload,
    )
    add_product.raise_for_status()


def get_cartproduct(cart_id, product_id):
    cartproduct_filter = {
        'filters[cart][$eq]': cart_id,
        'filters[product][$eq]': product_id,
    }
    cartproduct = requests.get(
        os.path.join(STRAPI_API_URL, 'product-in-carts'),
        headers=AUTH_HEADER,
        params=cartproduct_filter,
    )
    cartproduct.raise_for_status()
    return cartproduct.json()


def delete_cartproduct(cartproduct_id):
    delete_product = requests.delete(
        os.path.join(
            STRAPI_API_URL,
            'product-in-carts',
            str(cartproduct_id),
        ),
        headers=AUTH_HEADER,
    )
    delete_product.raise_for_status()


def get_user(cart_id):
    user_filter = {'filters[cart][$eq]': cart_id}
    user = requests.get(
        os.path.join(STRAPI_API_URL, 'users'),
        headers=AUTH_HEADER,
        params=user_filter,
    )
    user.raise_for_status()
    return user.json()


def save_email(user_id, email):
    payload = {'email': email}
    update_response = requests.put(
        os.path.join(STRAPI_API_URL, 'users', str(user_id)),
        headers=AUTH_HEADER,
        json=payload,
    )
    update_response.raise_for_status()
