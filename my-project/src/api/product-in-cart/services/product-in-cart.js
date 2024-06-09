'use strict';

/**
 * product-in-cart service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::product-in-cart.product-in-cart');
