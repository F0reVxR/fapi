let button = document.getElementById('toggle')

button.addEventListener('click', () => {
    document.body.classList.toggle("dark");
    button.classList.toggle("dark");
})

let profileDiv = document.getElementById('ave')
let imageChangeStatus = false

function importImage(){
    let img = document.createElement('input')
    img.classList.add('uploading')
    img.type = 'file'
    
    return img
}

function createImage(){
    let image = document.createElement('img');
    image.classList.add('profile-picture');
    image.src = '';
    image.alt = 'profile-picture';

    return image
}

function choosePfp(){
    let existingImg = document.getElementsByClassName('profile-picture')
    existingImg.remove()
    

    let img = createImage()
    profileDiv.append(img)
}

profileDiv.addEventListener('click', choosePfp)
