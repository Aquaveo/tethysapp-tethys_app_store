const addModalHelper = {
  validationResults: (validationData, content, completeMessage, ws ) =>{
    if(!validationData.metadata['next_move']){
      // $("#failMessage").html(validationData.mssge_string)
      // $("#failMessage").show()


      $(`#tethysapp_${validationData.conda_channel}_failMessage`).html(validationData.mssge_string)
      $(`#tethysapp_${validationData.conda_channel}_failMessage`).show()
      $(`#tethysapp_${validationData.conda_channel}-spinner`).hide();
      $("#submitTethysAppLoaderEllipsis").hide()
      $("#submitTethysAppLoaderText").text("")
      $("#fetchRepoButton").prop("disabled", false)
    }
    else{
      // $("#failMessage").html(validationData.mssge_string)
      // $("#failMessage").show()
      $(`#tethysapp_${validationData.conda_channel}_failMessage`).html(validationData.mssge_string)
      $(`#tethysapp_${validationData.conda_channel}_failMessage`).show()
      notification_ws.send(
          JSON.stringify({
              data: {
                  url: validationData.metadata['submission_github_url']
              },
              type: `pull_git_repo`
          })
      )
    }

  },
  showBranches: (branchesData, content, completeMessage, ws) => {
    // Clear loader and button:

    $("#submitTethysAppLoaderEllipsis").hide()
    $("#fetchRepoButton").hide()
    $("#submitTethysAppLoaderText").text("")

    if (!("branches" in branchesData)) {
      sendNotification(
        "Error while checking the repo for branches. Please ensure the repo is public.", $(".branchesList")
      )
      return
    }

    let branches = branchesData["branches"]
    let conda_channel = branchesData["conda_channel"]
    let conda_labels = branchesData["conda_labels"]
    let app_name = branchesData["app_name"]

    if (branches.length == 1) {
      $(`#tethysapp_${conda_channel}-spinner`).show(); 

      sendNotification(
        `One branch found. Continuing packaging with ${branches[0]} branch.`,
        $(".branchesList")

      )
      $("#submitTethysAppLoaderEllipsis").show()
      $("#processBranchButton").prop("disabled", true)
      $("#submitTethysAppLoaderText").text(`Please wait. Processing branch: ${branches[0]}`)

      notification_ws.send(
        JSON.stringify({
          data: {
            branch: branches[0],
            app_name: app_name,
            conda_channel: conda_channel,
            conda_labels: conda_labels,
            email: $("#tethysapp_notifEmail").val(),
            dev_url: $("#tethysapp_githubURL").val()

          },
          type: `submit_tethysapp_to_store`
        })
      )
      return
    }

    // More than one branch available. Ask user for option:
    let branchesHTML = htmlHelpers.getBranches(conda_channel, branches)
    // $("#branchesList").append(branchesHTML)
    $(`#tethysapp_${conda_channel}_branchesList`).append(branchesHTML)

    $("#processBranchButton").click((e) => {
      $(`#tethysapp_${conda_channel}-spinner`).show();

      let branchName = $(`#${conda_channel}_add_branch`).val()

      $("#submitTethysAppLoaderEllipsis").show()
      $("#processBranchButton").prop("disabled", true)
      $("#submitTethysAppLoaderText").text( `Please wait. Processing branch: ${branchName}`)

      notification_ws.send(
        JSON.stringify({
          data: {
            branch: branchName,
            app_name: app_name,
            conda_channel: conda_channel,
            conda_labels: conda_labels,
            email: $("#tethysapp_notifEmail").val(),
            dev_url: $("#tethysapp_githubURL").val()
          },
          type: `submit_tethysapp_to_store`
        })
      )
    })
    $("#processBranchButton").show()
    // $("#failMessage").hide()
    $(`#tethysapp${conda_channel}_failMessage`).hide()
  },

  tethysAppSubmitComplete: (addData, content, completeMessage, ws) => {
    $("#submitTethysAppLoaderEllipsis").hide()
    $("#processBranchButton").hide()
    $("#tethysappSubmitCancel").hide()
    $("#submitTethysAppLoaderText").text("")
    if (addData.job_url) {
      
      $(`#tethysapp_${addData.conda_channel}_addSuccessLink`).html(
        `<a href="${addData.job_url}" target="_blank">here</a>`
      )
    } else {
      // Hide the link part of the success message
      $(`#tethysapp_${addData.conda_channel}_SuccessLinkMessage`).hide();
    }
    $("#tethysappSubmitDone").show()
    $(`#tethysapp_${addData.conda_channel}_successMessage`).show();
    $(`#tethysapp_${addData.conda_channel}_failMessage`).hide()
    $(`#tethysapp_${addData.conda_channel}-spinner`).hide(); 
  },

  
  proxyAppSubmitComplete: (addData, content, completeMessage, ws) => {
    $("#submitProxyAppLoaderEllipsis").hide()
    $("#submitProxyAppLoaderText").text("")
    $("#proxyappSubmitCancel").hide()
    if (addData.job_url) {
      
      $(`#proxyapp_${addData.conda_channel}_addSuccessLink`).html(
        `<a href="${addData.job_url}" target="_blank">here</a>`
      )
    } else {
      $(`#proxyapp_${addData.conda_channel}_SuccessLinkMessage`).hide();
    }
    $("#submitProxyApp").hide()
    $("#proxyappSubmitDone").show()
    $(`#proxyapp_${addData.conda_channel}_successMessage`).show();
    $(`#proxyapp_${addData.conda_channel}_failMessage`).hide()
    $(`#proxyapp_${addData.conda_channel}-spinner`).hide(); 
  },

  
  proxyAppInstallComplete: (addData, content, completeMessage, ws) => {
    sendNotification("install_complete", content)
  }
}

const getTethysSubmitModalInput = (modal_type) => {
  let githubURL = $(`#${modal_type}_githubURL`).val()
  let notifEmail = $(`#${modal_type}_notifEmail`).val()

  let active_stores = []
  availableStores = $(`#${modal_type}_availableStores`).children(".row_store_submission")
  for (let i = 0; i < availableStores.length; i++) {
    let input_store = {"conda_channel": "", "conda_labels": []}
    let store = availableStores[i]
    let channel_checkbox = $(store).find(".conda-channel-list-item")[0]
    if (!channel_checkbox.checked) {
      continue;
    }
    input_store["conda_channel"] = channel_checkbox.value

    let labels_checkboxes = $(store).find(".conda-label-list-item")
    for (let x = 0; x < labels_checkboxes.length; x++) {
      let label_checkbox = labels_checkboxes[x]
      if (!label_checkbox.checked) {
        continue;
      }
      input_store["conda_labels"].push(label_checkbox.value)
    }

    active_stores.push(input_store)
  }

  return [githubURL, notifEmail, active_stores]
}

const disableSubmitAppModalInput = (modal_type, disable_options) => {
  let SubmitAppModal = $(`#submit-${modal_type}-to-store-modal`)
  if (disable_options['disable_email']) {
    SubmitAppModal.find(".notifEmail").prop("disabled", true)
    SubmitAppModal.find(".notifEmail").css('opacity', '.5');
  }

  if (disable_options['disable_gihuburl']) {
    SubmitAppModal.find(".githubURL").prop("disabled", true)
    SubmitAppModal.find(".githubURL").css('opacity', '.5');
  }
  
  if (disable_options['disable_channels']) {
    SubmitAppModal.find(".conda-channel-list-item").each(function() {
      $(this).prop("disabled", true)
    })
    
    SubmitAppModal.find(".conda-channel-list-item-custom-checkbox").each(function() {
      $(this).css('background-color', 'lightgray');
      $(this).css('opacity', '.5');
    })
  }

  if (disable_options['disable_labels']) {
    SubmitAppModal.find(".conda-label-list-item").each(function() {
      $(this).prop("disabled", true)
    })
    
    SubmitAppModal.find(".conda-label-list-item-custom-checkbox").each(function() {
      $(this).css('background-color', 'lightgray');
      $(this).css('opacity', '.5');
    })
  }

  if (disable_options['disable_branches']) {
    SubmitAppModal.find(".add_branch").each(function() {
      $(this).prop("disabled", true)
      $(this).css('opacity', '.5');
    })
  }
}

const getProxyModalInput = (modal_name) => {
  let ProxyAppModal = $(`#${modal_name}`)
  let proxyAppName = ProxyAppModal.find("#proxyAppName").val()
  let proxyEndpoint = ProxyAppModal.find("#proxyEndpoint").val()
  let proxyDescription = ProxyAppModal.find("#proxyDescription").val()
  let proxyLogo = ProxyAppModal.find("#proxyLogo").val()
  let proxyTags = []
  ProxyAppModal.find("#proxyTagList").find(".tag-item").each(function () {
    let tag = this.innerText
    tag = tag.substring(0, tag.length-1)
    proxyTags.push(tag)
  })
  let proxyEnabled = ProxyAppModal.find("#proxyEnabled")[0].checked
  let proxyShown = ProxyAppModal.find("#proxyShown")[0].checked

  return [proxyAppName, proxyEndpoint, proxyDescription, proxyLogo, proxyTags, proxyEnabled, proxyShown]
}

const disableProxyAppModalInput = (modal_name) => {
  let ProxyAppModal = $(`#${modal_name}`)
  ProxyAppModal.find("#proxyAppName").prop("disabled", true)
  ProxyAppModal.find("#proxyAppName").css('opacity', '.5');

  ProxyAppModal.find("#proxyEndpoint").prop("disabled", true)
  ProxyAppModal.find("#proxyEndpoint").css('opacity', '.5');

  ProxyAppModal.find("#proxyDescription").prop("disabled", true)
  ProxyAppModal.find("#proxyDescription").css('opacity', '.5');

  ProxyAppModal.find("#proxyLogo").prop("disabled", true)
  ProxyAppModal.find("#proxyLogo").css('opacity', '.5');

  ProxyAppModal.find("#proxyTags").prop("disabled", true)
  ProxyAppModal.find("#proxyTags").css('opacity', '.5');

  ProxyAppModal.find(".tag-item-delete").each(function() {
    $(this).prop("disabled", true)
    $(this).css('opacity', '.5');
  })

  ProxyAppModal.find("#proxyEnabled").prop("disabled", true)
  ProxyAppModal.find("#proxyEnabled").css('opacity', '.5');

  ProxyAppModal.find("#proxyShown").prop("disabled", true)
  ProxyAppModal.find("#proxyShown").css('opacity', '.5');
}

const createProxyApp = () => {
  $(".proxyApp_failMessage").hide()
  let [proxyAppName, proxyEndpoint, proxyDescription, proxyLogo, proxyTags, proxyEnabled, proxyShown] = getProxyModalInput("add-proxyapp-to-portal-modal")

  let errors = false
  if (!proxyAppName) {
    $("#proxyAppName_failMessage").show()
    errors = true
  }

  if (!proxyEndpoint) {
    $("#proxyEndpoint_failMessage").show()
    errors = true
  }

  if (errors) {
    return
  }

  disableProxyAppModalInput("add-proxyapp-to-portal-modal")
  notification_ws.send(
      JSON.stringify({
          data: {
              app_name: proxyAppName,
              endpoint: proxyEndpoint, 
              description: proxyDescription, 
              logo_url: proxyLogo, 
              tags: proxyTags, 
              enabled: proxyEnabled, 
              show_in_apps_library: proxyShown
          },
          type: `create_proxy_app`
      })
  )
  location.reload();
}

const getRepoForAdd = () => {
  $(".label_failMessage").hide()
  $(".tethysapp_failMessage").hide()
  let [githubURL, notifEmail, active_stores] = getTethysSubmitModalInput("tethysapp")

  let errors = false
  if (!githubURL) {
    $("#tethysapp_githubURL_failMessage").show()
    errors = true
  }

  if (!notifEmail) {
    $("#tethysapp_notifEmail_failMessage").show()
    errors = true
  }

  if (active_stores.length == 0) {
    $('#tethysapp_channel_failMessage').show()
    errors = true
  } else {
    for (let i = 0; i < active_stores.length; i++) {
      if (active_stores[i].conda_labels.length == 0) {
        $(`#tethysapp_${active_stores[i].conda_channel}_label_failMessage`).show()
        errors = true
      }
    }
  }

  if (errors) {
    return
  }

  $("#submitTethysAppLoaderEllipsis").show()
  $("#fetchRepoButton").prop("disabled", true)
  $("#submitTethysAppLoaderText").text("Please wait. Fetching GitHub Repo")
  disable_options = {
    disable_email: true, disable_gihuburl: true, disable_channels: true, disable_labels: true, disable_branches: false
  }
  disableSubmitAppModalInput("tethysapp", disable_options)
  notification_ws.send(
      JSON.stringify({
          data: {
              url: githubURL,
              stores: active_stores
          },
          type: `initialize_local_repo_for_active_stores`
      })
  )
}

function UpdateProxyApp() {
  $(".proxyApp_failMessage").hide()
  let [proxyAppName, proxyEndpoint, proxyDescription, proxyLogo, proxyTags, proxyEnabled, proxyShown] = getProxyModalInput("update-proxyapp-modal")

  let errors = false
  if (!proxyAppName) {
    $("#proxyAppName_failMessage").show()
    errors = true
  }

  if (!proxyEndpoint) {
    $("#proxyEndpoint_failMessage").show()
    errors = true
  }

  if (errors) {
    return
  }

  disableProxyAppModalInput("update-proxyapp-modal")
  notification_ws.send(
      JSON.stringify({
          data: {
              app_name: proxyAppName,
              endpoint: proxyEndpoint, 
              description: proxyDescription, 
              logo_url: proxyLogo, 
              tags: proxyTags, 
              enabled: proxyEnabled, 
              show_in_apps_library: proxyShown
          },
          type: `update_proxy_app`
      })
  )
  location.reload();
}

$(document).on('click', ".anchor", function() {
  let checkList = $(this).parents(".dropdown-check-list-labels")[0]
  if (checkList.classList.contains('visible')){
    checkList.classList.remove('visible');
  }
  else{
    checkList.classList.add('visible');
  }
})

$(document).on('change', ".conda-channel-list-item", function() {
  let channel_select = $(this).parents(".dropdown-check-list-channels")
  let label_select = channel_select.siblings(".dropdown-check-list-labels")[0];
  if(this.checked){
    label_select.classList.remove('d-none')
  } else {
    label_select.classList.add('d-none')
  }

  let branch_selects = channel_select.siblings(".branches-list");
  if (branch_selects.length > 0) {
    let branch_select = branch_selects[0];
    if(this.checked){
      branch_select.classList.remove('d-none')
    } else {
      branch_select.classList.add('d-none')
    }
  }
})

$(document).on('hidden.bs.modal', '#submit-tethysapp-to-store-modal', function() {
  $('#submit-tethysapp-to-store-modal').remove();
  var originalTethysSubmitStoreModalClone = originalTethysSubmitStoreModal.clone();
  $('body').append(originalTethysSubmitStoreModalClone);
});

$(document).on('hidden.bs.modal', '#add-proxyapp-to-portal-modal', function() {
  $('#add-proxyapp-to-portal-modal').remove();
  var originalProxyAddPortalModalClone = originalProxyAddPortalModal.clone();
  $('body').append(originalProxyAddPortalModalClone);
});

$(document).on('hidden.bs.modal', '#submit-proxyapp-to-store-modal', function() {
  $('#submit-proxyapp-to-store-modal').remove();
  var originalProxySubmitStoreModalClone = originalProxySubmitStoreModal.clone();
  $('body').append(originalProxySubmitStoreModalClone);
});


$(document).on('keydown', '#proxyTags', function(event) {
  const tags = $(this).siblings("#proxyTagList")[0]; 

  if (event.key === 'Enter' || event.key === 'Tab') { 
      event.preventDefault(); 
      const tag = document.createElement('li');
      const tagContent = this.value.trim(); 
      if (tagContent !== '') {
        tag.innerText = tagContent;
        tag.classList.add("tag-item");
        tag.innerHTML += '<button class="tag-item-delete">X</button>'; 
        tags.appendChild(tag);
        this.value = ''; 
    } 
  } 
});


$(document).on('click', '#proxyTagList', function(event) {
  if (event.target.classList.contains('tag-item-delete')) { 
    event.target.parentNode.remove(); 
  } 
});


$(document).on('click', '.proxyAppDelete', function(event) {
  let proxyAppName = this.id.split("_")[0]
  notification_ws.send(
    JSON.stringify({
        data: {
          app_name: proxyAppName
        },
        type: `delete_proxy_app`
    })
  )
  location.reload();
});


$(document).on('click', '.proxyAppUpdate', function(event) {
  let proxyAppName = this.id.split("_")[0]
  let proxyApp = proxyApps.filter(obj => {return obj.name === proxyAppName})[0]
  let updateProxyAppModal = $('#update-proxyapp-modal')
  updateProxyAppModal.find("#proxyAppName")[0].value = proxyAppName
  updateProxyAppModal.find("#proxyEndpoint")[0].value = proxyApp['endpoint']
  updateProxyAppModal.find("#proxyDescription")[0].value = proxyApp['description']
  updateProxyAppModal.find("#proxyLogo")[0].value = proxyApp['logo']
  updateProxyAppModal.find("#proxyEnabled")[0].checked = proxyApp['enabled']
  updateProxyAppModal.find("#proxyShown")[0].checked = proxyApp['show_in_apps_library']

  let proxyTagList = updateProxyAppModal.find("#proxyTagList")
  proxyTagList.empty()
  proxyApp['tags'].split(",").forEach(function (tag_value) {
    const tag = document.createElement('li');
    if (tag_value !== '') {
      tag.innerText = tag_value;
      tag.classList.add("tag-item");
      tag.innerHTML += '<button class="tag-item-delete">X</button>'; 
      proxyTagList[0].appendChild(tag);
    }
  })
  updateProxyAppModal.modal('show');
});


$(document).on('click', '.proxyAppUploadToStore', function(event) {
  let proxyAppName = this.id.split("_")[0]
  let submitProxyAppModal = $('#submit-proxyapp-to-store-modal')
  submitProxyAppModal.find(".modal-header").find("#submitProxyAppName")[0].innerHTML = proxyAppName
  submitProxyAppModal.find(".modal-footer").find("#submitProxyAppName")[0].innerHTML = proxyAppName
  submitProxyAppModal.modal("show")
});


$(document).on('click', '#submitProxyApp', function(event) {
  $(".label_failMessage").hide()
  $(".proxyapp_failMessage").hide()
  let submitProxyAppModal = $('#submit-proxyapp-to-store-modal')
  let proxyAppName = submitProxyAppModal.find(".modal-header").find("#submitProxyAppName")[0].innerHTML
  let [_, notifEmail, active_stores] = getTethysSubmitModalInput("proxyapp")

  let errors = false
  if (!notifEmail) {
    $("#proxyapp_notifEmail_failMessage").show()
    errors = true
  }

  if (active_stores.length == 0) {
    $('#proxyapp_channel_failMessage').show()
    errors = true
  } else {
    for (let i = 0; i < active_stores.length; i++) {
      if (active_stores[i].conda_labels.length == 0) {
        $(`#proxyapp_${active_stores[i].conda_channel}_label_failMessage`).show()
        errors = true
      }
    }
  }

  if (errors) {
    return
  }

  disable_options = {
    disable_email: true, disable_gihuburl: false, disable_channels: true, disable_labels: true, disable_branches: false
  }
  disableSubmitAppModalInput("proxyapp", disable_options)
  $("#submitProxyAppLoaderEllipsis").show()
  $("#submitProxyAppLoaderText").text( `Please wait. Submitting ${proxyAppName} to the app store`)
  $("#submitProxyApp").prop("disabled", true)
  notification_ws.send(
      JSON.stringify({
          data: {
              app_name: proxyAppName,
              active_stores: active_stores,
              notification_email: notifEmail
          },
          type: `submit_proxy_app`
      })
  )
});
