from io import BytesIO
import os

import requests


def get_products(strapi_token, strapi_api_url):
    products = requests.get(
        os.path.join(strapi_api_url, 'products'),
        headers={'Authorization': f'bearer {strapi_token}', },
    )
    products.raise_for_status()
    return products.json()


def get_product_with_picture(product_id, strapi_token, strapi_api_url):
    payload = {'populate': 'picture'}
    product = requests.get(
        os.path.join(strapi_api_url, 'products', product_id),
        headers={'Authorization': f'bearer {strapi_token}', },
        params=payload,
    )
    product.raise_for_status()
    return product.json()


def download_picture(picture_url, strapi_api_url):
    picture_url = os.path.join(strapi_api_url[:-4], picture_url,)
    picture_response = requests.get(picture_url)
    picture_response.raise_for_status()
    return BytesIO(picture_response.content)


def get_cart(telegram_id, strapi_token, strapi_api_url):
    cart_filter = {
            'filters[tg_id][$eq]': telegram_id,
            'populate[cartproducts][populate]': 'product',
        }
    user_cart = requests.get(
        os.path.join(strapi_api_url, 'carts'),
        headers={'Authorization': f'bearer {strapi_token}', },
        params=cart_filter,
    )
    user_cart.raise_for_status()
    return user_cart.json()


def create_cart(telegram_id, strapi_token, strapi_api_url):
    cart_payload = {
        'data': {'tg_id': telegram_id},
    }
    create_cart = requests.post(
        os.path.join(strapi_api_url, 'carts'),
        headers={'Authorization': f'bearer {strapi_token}', },
        json=cart_payload,
    )
    create_cart.raise_for_status()


def add_product(cart_id, product_id, amount, strapi_token, strapi_api_url):
    productcart_payload = {
        'data': {
            'cart': cart_id,
            'product': product_id,
            'amount': amount,
        }
    }
    add_product = requests.post(
        os.path.join(strapi_api_url, 'product-in-carts'),
        headers={'Authorization': f'bearer {strapi_token}', },
        json=productcart_payload,
    )
    add_product.raise_for_status()


def get_cartproduct(cart_id, product_id, strapi_token, strapi_api_url):
    cartproduct_filter = {
        'filters[cart][$eq]': cart_id,
        'filters[product][$eq]': product_id,
    }
    cartproduct = requests.get(
        os.path.join(strapi_api_url, 'product-in-carts'),
        headers={'Authorization': f'bearer {strapi_token}', },
        params=cartproduct_filter,
    )
    cartproduct.raise_for_status()
    return cartproduct.json()


def delete_cartproduct(cartproduct_id, strapi_token, strapi_api_url):
    delete_product = requests.delete(
        os.path.join(
            strapi_api_url,
            'product-in-carts',
            str(cartproduct_id),
        ),
        headers={'Authorization': f'bearer {strapi_token}', },
    )
    delete_product.raise_for_status()


def get_user(cart_id, strapi_token, strapi_api_url):
    user_filter = {'filters[cart][$eq]': cart_id}
    user = requests.get(
        os.path.join(strapi_api_url, 'users'),
        headers={'Authorization': f'bearer {strapi_token}', },
        params=user_filter,
    )
    user.raise_for_status()
    return user.json()


def save_email(user_id, email, strapi_token, strapi_api_url):
    payload = {'email': email}
    update_response = requests.put(
        os.path.join(strapi_api_url, 'users', str(user_id)),
        headers={'Authorization': f'bearer {strapi_token}', },
        json=payload,
    )
    update_response.raise_for_status()
