const addModalHelper = {
  validationResults: (validationData, content, completeMessage, ws ) =>{
    if(!validationData.metadata['next_move']){
      // $("#failMessage").html(validationData.mssge_string)
      // $("#failMessage").show()


      $(`#${validationData.conda_channel}_failMessage`).html(validationData.mssge_string)
      $(`#${validationData.conda_channel}_failMessage`).show()
      $(`#${validationData.conda_channel}_spinner`).hide();
      $("#loaderEllipsis").hide()
      $("#loadingTextAppSubmit").text("")
      $("#fetchRepoButton").prop("disabled", false)
    }
    else{
      // $("#failMessage").html(validationData.mssge_string)
      // $("#failMessage").show()
      $(`#${validationData.conda_channel}_failMessage`).html(validationData.mssge_string)
      $(`#${validationData.conda_channel}_failMessage`).show()
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

    $("#loaderEllipsis").hide()
    $("#fetchRepoButton").hide()
    $("#loadingTextAppSubmit").text("")

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
      $(`#${conda_channel}_spinner`).show(); 

      sendNotification(
        `One branch found. Continuing packaging with ${branches[0]} branch.`,
        // $("#branchesList")
        $(".branchesList")

      )
      $("#loaderEllipsis").show()
      $("#processBranchButton").prop("disabled", true)
      $("#loadingTextAppSubmit").text(`Please wait. Processing branch: ${branches[0]}`)

      // notification_ws.send(
      //   JSON.stringify({
      //       data: {
      //           url: githubURL
      //       },
      //       type: `validate_git_repo`
      //   })
      // )

      notification_ws.send(
        JSON.stringify({
          data: {
            branch: branches[0],
            app_name: app_name,
            conda_channel: conda_channel,
            conda_labels: conda_labels,
            email: $("#notifEmail").val(),
            dev_url: $("#githubURL").val()

          },
          type: `process_branch`
        })
      )
      return
    }

    // More than one branch available. Ask user for option:
    let branchesHTML = htmlHelpers.getBranches(conda_channel, branches)
    // $("#branchesList").append(branchesHTML)
    $(`#${conda_channel}_branchesList`).append(branchesHTML)

    $("#processBranchButton").click((e) => {
      $(`#${conda_channel}_spinner`).show();

      let branchName = $(`#${conda_channel}_add_branch`).val()

      $("#loaderEllipsis").show()
      $("#processBranchButton").prop("disabled", true)
      $("#loadingTextAppSubmit").text( `Please wait. Processing branch: ${branchName}`)

      notification_ws.send(
        JSON.stringify({
          data: {
            branch: branchName,
            app_name: app_name,
            conda_channel: conda_channel,
            conda_labels: conda_labels,
            email: $("#notifEmail").val(),
            dev_url: $("#githubURL").val()
          },
          type: `process_branch`
        })
      )
    })
    $("#processBranchButton").show()
    // $("#failMessage").hide()
    $(`#${conda_channel}_failMessage`).hide()


  },
  addComplete: (addData, content, completeMessage, ws) => {
    $("#loaderEllipsis").hide()
    $("#processBranchButton").hide()
    $("#cancelAddButton").hide()
    $("#loadingTextAppSubmit").text("")
    if (addData.job_url) {
      
      $(`#${addData.conda_channel}_addSuccessLink`).html(
        `<a href="${addData.job_url}" target="_blank">here</a>`
      )
      // $("#addSuccessLink").html(
      //   `<a href="${addData.job_url}" target="_blank">here</a>`
      // )
      
    } else {
      // Hide the link part of the success message
      $(`#${addData.conda_channel}_SuccessLinkMessage`).hide();
      // $("#SuccessLinkMessage").hide()

    }
    $("#doneAddButton").show()
    $("#submitNewButton").show()
    $(`#${addData.conda_channel}_successMessage`).show();
    $(`#${addData.conda_channel}_failMessage`).hide()
    $(`#${addData.conda_channel}_spinner`).hide(); 
  }
}

const getModalInput = () => {
  let githubURL = $("#githubURL")[0].value

  let notifEmail = $("#notifEmail")[0].value

  let active_stores = []
  availableStores = $("#availableStores").children(".row_store_submission")
  for (let i = 0; i < availableStores.length; i++) {
    let input_store = {"conda_channel": "", "conda_labels": []}
    let store = availableStores[i]
    let channel_checkbox = $(store).find(".conda-channel-list-item")[0]
    if (!channel_checkbox.checked) {
      break;
    }
    input_store["conda_channel"] = channel_checkbox.value

    let labels_checkboxes = $(store).find(".conda-label-list-item")
    for (let x = 0; x < labels_checkboxes.length; x++) {
      let label_checkbox = labels_checkboxes[x]
      if (!label_checkbox.checked) {
        break;
      }
      input_store["conda_labels"].push(label_checkbox.value)
    }

    active_stores.push(input_store)
  }

  return [githubURL, notifEmail, active_stores]
}

const disableModalInput = (disable_email=false, disable_gihuburl=false, disable_channels=false, disable_labels=false, disable_branches=false) => {

  if (disable_email) {
    $("#notifEmail").prop("disabled", true)
    $("#notifEmail").css('opacity', '.5');
  }

  if (disable_gihuburl) {
    $("#githubURL").prop("disabled", true)
    $("#githubURL").css('opacity', '.5');
  }
  
  if (disable_channels) {
    $(".conda-channel-list-item").each(function() {
      $(this).prop("disabled", true)
    })
    
    $(".conda-channel-list-item-custom-checkbox").each(function() {
      $(this).css('background-color', 'lightgray');
      $(this).css('opacity', '.5');
    })
  }

  if (disable_labels) {
    $(".conda-label-list-item").each(function() {
      $(this).prop("disabled", true)
    })
    
    $(".conda-label-list-item-custom-checkbox").each(function() {
      $(this).css('background-color', 'lightgray');
      $(this).css('opacity', '.5');
    })
  }

  if (disable_branches) {
    $(".add_branch").each(function() {
      $(this).prop("disabled", true)
      $(this).css('opacity', '.5');
    })
  }
}

const getRepoForAdd = () => {
  $("#notifEmail_failMessage").hide()
  $("#githubURL_failMessage").hide()
  $(".label_failMessage").hide()
  $('#channel_failMessage').hide()
  let [githubURL, notifEmail, active_stores] = getModalInput()

  let errors = false
  if (!githubURL) {
    $("#githubURL_failMessage").show()
    errors = true
  }

  if (!notifEmail) {
    $("#notifEmail_failMessage").show()
    errors = true
  }

  if (active_stores.length == 0) {
    $('#channel_failMessage').show()
    errors = true
  } else {
    for (let i = 0; i < active_stores.length; i++) {
      if (active_stores[i].conda_labels.length == 0) {
        $(`#${active_stores[i].conda_channel}_label_failMessage`).show()
        errors = true
      }
    }
  }

  if (errors) {
    return
  }

  $("#loaderEllipsis").show()
  $("#fetchRepoButton").prop("disabled", true)
  $("#loadingTextAppSubmit").text("Please wait. Fetching GitHub Repo")
  disableModalInput(disable_email=true, disable_gihuburl=true, disable_channels=true, disable_labels=true)
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

$(document).on('click', ".anchor", function() {
  let checkList = $(this).parents(".dropdown-check-list")[0]
  if (checkList.classList.contains('visible')){
    checkList.classList.remove('visible');
  }
  else{
    checkList.classList.add('visible');
  }
})

$(document).on('change', ".conda-channel-list-item", function() {
  let conda_channel = this.id;
  let branch_select = $(`#${conda_channel}_branchesList`)[0];
  let label_select = $(`#${conda_channel}_labels`)[0];
  if(this.checked){
    label_select.classList.remove('d-none')
    branch_select.classList.remove('d-none')
  } else {
    label_select.classList.add('d-none')
    branch_select.classList.add('d-none')
  }
})

$(document).on('hidden.bs.modal', '#add-app-modal', function() {
  $('#add-app-modal').remove();
  var originalAddModalClone = originalAddModal.clone();
  $('body').append(originalAddModalClone);
});
