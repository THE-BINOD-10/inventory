$(document).ready(function() {

  $('#location_upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#download-location").text("Download Location Form");
        $("#location-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Locations Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#download-location").text("Download Error Form");
        $("#location-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Locations. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#combo-sku-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#download-combo-sku").text("Download Location Form");
        $("#combo-sku-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Combo SKU Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#download-combo-sku").text("Download Error Form");
        $("#combo-sku-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Combo SKU. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#supplier-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#download-supplier").text("Download Supplier Form");
        $("#supplier-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Suppliers Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else if (data.result == "Invalid File") {
        $('.top-right').notify({
          message: { text: 'Invalid File,Upload Correct File' },
          type: 'danger',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#download-supplier").text("Download Error Form");
        $("#supplier-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Suppliers. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#supplier-sku-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#download-supplier-sku").text("Download Supplier Form");
        $("#supplier-sku-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Suppliers-Sku Mappings Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else if (data.result == "No Supplier Id") {
        $('.top-right').notify({
          message: { text: 'Supplier Id not matched.' },
          type: 'warning',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();

      }
      else {
        $("#download-supplier-sku").text("Download Error Form");
        $("#supplier-sku-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Suppliers. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#fileupload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#upload-inventory").text("Download Inventory Form");
        $("#error-file").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Inventory Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#upload-inventory").text("Download Error Form");
        $("#error-file").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Inventory. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#sku-file').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#upload-sku").text("Download SKU Form");
        $("#sku-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'SKU form Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#upload-sku").text("Download Error Form");
        $("#sku-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload SKU form. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });


  $('#purchase-order-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#upload-sku").text("Download SKU Form");
        $("#sku-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Order form Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else if(data.result == "Invalid File")
      {
        $('.top-right').notify({
          message: { text: 'Invalid File' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'danger'
        }).show();

      }
      else {
        $("#download-purchase-order-form").text("Download Error Form");
        $("#purchase-order-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Order form. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });



  $('#order-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#order-upload").text("Download Order Form");
        $("#order-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Order form Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else if (data.result == "Invalid File") {
        $('.top-right').notify({
          message: { text: 'Invalid File Uploaded' },
          type: 'danger',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#download-order-form").text("Download Error Form");
        $("#order-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Order form. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#move-inventory-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#upload-sku").text("Download SKU Form");
        $("#sku-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Move Inventory form Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#move-inventory-location").text("Download Error Form");
        $("#move-inventory-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Move Inventory form. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#marketplace-sku-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#download-marketplace-sku").text("Download Market SKU Form");
        $("#marketplace-sku-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Market Place Sku form Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#download-marketplace-sku").text("Download Error Form");
        $("#marketplace-sku-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Market Place SKU form. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#bom-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#download-bom").text("Download BOM Form");
        $("#bom-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'BOM form Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#download-bom").text("Download Error Form");
        $("#bom-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload BOM form. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

  $('#inventory-adjust-upload').fileupload({
    add: function (e, data) {
      data.context = $(".loading").removeClass('display-none');
      data.submit();
    },
    done: function (e, data) {
      $(".loading").addClass('display-none');
      if (data.result == "Success") {
        $("#download-inventory-adjust").text("Download Adjustment Form");
        $("#inventory-adjust-error").attr("value", "");
        $('.top-right').notify({
          message: { text: 'Inventory Adjustment form Uploaded Successfully' },
          type: 'success',
          fadeOut: { enabled: true, delay: 6000 },
        }).show();
      }
      else {
        $("#download-inventory-adjust").text("Download Error Form");
        $("#inventory-adjust-error").attr("value", data.result);
        $('.top-right').notify({
          message: { text: 'Failed to Upload Inventory Adjustment form. Please download the error form' },
          fadeOut: { enabled: true, delay: 6000 },
          type: 'warning'
        }).show();
      }
    }
  });

});
