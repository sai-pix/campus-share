
document.addEventListener("DOMContentLoaded", function () {

    const input = document.getElementById("roomImages");
    const preview = document.getElementById("roomImagePreview");

    if (!input || !preview) return;

    let selectedFiles = [];

    input.addEventListener("change", function () {

        const newFiles = Array.from(input.files);

        selectedFiles = [...selectedFiles, ...newFiles];

        if (selectedFiles.length > 5) {
            alert("You can upload a maximum of 5 photos.");
            selectedFiles = selectedFiles.slice(0, 5);
        }

        if (selectedFiles.some(file =>
            !["image/jpeg", "image/png", "image/webp"].includes(file.type)
        )) {
            alert("Only JPG, PNG and WEBP images are allowed.");
            selectedFiles = [];
        }

        if (selectedFiles.some(file => file.size > 5 * 1024 * 1024)) {
            alert("Each image must be smaller than 5 MB.");
            selectedFiles = [];
        }

        updatePreview();
    });

    function updatePreview() {

        preview.innerHTML = "";

        const dataTransfer = new DataTransfer();

        selectedFiles.forEach((file, index) => {

            dataTransfer.items.add(file);

            const reader = new FileReader();

            reader.onload = function (event) {

                const card = document.createElement("div");
                card.className = "room-preview-card";

                const image = document.createElement("img");
                image.src = event.target.result;
                image.alt = "Room photo " + (index + 1);

                const remove = document.createElement("button");
                remove.type = "button";
                remove.textContent = "×";
                remove.setAttribute("aria-label", "Remove photo");

                remove.addEventListener("click", function () {
                    selectedFiles.splice(index, 1);
                    updatePreview();
                });

                card.appendChild(image);
                card.appendChild(remove);
                preview.appendChild(card);
            };

            reader.readAsDataURL(file);
        });

        input.files = dataTransfer.files;
    }

    document.getElementById("roomForm").addEventListener("submit", function (event) {
        if (selectedFiles.length < 2 || selectedFiles.length > 5) {
            event.preventDefault();
            alert("Please select at least 2 and at most 5 photos.");
        }
    });

});
