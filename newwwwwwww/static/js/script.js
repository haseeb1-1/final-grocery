// static/js/script.js
// Cart functionality
document.addEventListener('DOMContentLoaded', function() {
    const cartBtn = document.getElementById('cartBtn');
    const cartModal = document.getElementById('cartModal');
    const closeCart = document.getElementById('closeCart');
    
    if (cartBtn && cartModal) {
        cartBtn.addEventListener('click', function() {
            cartModal.classList.add('active');
            loadCartItems();
        });
        
        closeCart.addEventListener('click', function() {
            cartModal.classList.remove('active');
        });
        
        cartModal.addEventListener('click', function(e) {
            if (e.target === cartModal) {
                cartModal.classList.remove('active');
            }
        });
    }
    
    // Quantity Controls
    document.querySelectorAll('.quantity-btn').forEach(button => {
        button.addEventListener('click', function() {
            const quantityElement = this.parentElement.querySelector('.quantity');
            let quantity = parseInt(quantityElement.textContent);
            
            if (this.textContent === '+') {
                quantity++;
            } else if (this.textContent === '-' && quantity > 1) {
                quantity--;
            }
            
            quantityElement.textContent = quantity;
        });
    });
});

function loadCartItems() {
    // This would typically fetch cart items from the server
    // For now, we'll use the existing cart items in the page
    console.log('Loading cart items...');
}

function updateCartCount(count) {
    const cartCount = document.getElementById('cartCount');
    if (cartCount) {
        cartCount.textContent = count;
    }
}