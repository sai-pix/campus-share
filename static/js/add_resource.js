
document.addEventListener("DOMContentLoaded", function () {

    const imageInput = document.getElementById("resource_image");
    const imagePreview = document.getElementById("imagePreview");
    const previewContainer = document.getElementById("previewContainer");
    const removeImageButton = document.getElementById("removeImage");

    if (!imageInput || !imagePreview || !previewContainer) {
        return;
    }

    imageInput.addEventListener("change", function () {

        const file = this.files[0];

        if (!file) {
            return;
        }

        const allowedTypes = [
            "image/jpeg",
            "image/png",
            "image/webp"
        ];

        if (!allowedTypes.includes(file.type)) {
            alert("Please select a JPG, PNG or WEBP image.");
            this.value = "";
            previewContainer.style.display = "none";
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert("Image size must be less than 5 MB.");
            this.value = "";
            previewContainer.style.display = "none";
            return;
        }

        const reader = new FileReader();

        reader.onload = function (event) {
            imagePreview.src = event.target.result;
            previewContainer.style.display = "block";
        };

        reader.readAsDataURL(file);
    });

    if (removeImageButton) {
        removeImageButton.addEventListener("click", function () {
            imageInput.value = "";
            imagePreview.src = "";
            previewContainer.style.display = "none";
        });
    }

});
