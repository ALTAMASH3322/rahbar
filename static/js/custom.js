
function loadBankDetails() {
    // Since data is already available in Jinja, no need to fetch it
    document.getElementById("bank_name").value = "{{ bank_details.bank_name or '' }}";
    document.getElementById("account_number").value = "{{ bank_details.account_number or '' }}";
    document.getElementById("account_name").value = "{{ bank_details.account_name or '' }}";
    document.getElementById("ifsc_code").value = "{{ bank_details.ifsc_code or '' }}";
}
    
function saveBankDetails() {
        // Get the latest values from the input fields
        var formData = {
            bank_name: document.getElementById("bank_name").value.trim(),
            account_number: document.getElementById("account_number").value.trim(),
            account_name: document.getElementById("account_name").value.trim(),
            ifsc_code: document.getElementById("ifsc_code").value.trim()
        };

        console.log("Updated Data Before Sending:", formData); // ✅ Debugging log

        fetch("{{ url_for('student.edit_bank_details') }}", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            console.log("Response:", data); // ✅ Debugging log
            alert(data.message);
            if (data.success) {
                location.reload();
            }
        })
        .catch(error => console.error("Error updating bank details:", error));
    }