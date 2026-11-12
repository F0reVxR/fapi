button = document.getElementById('toggle')

button.addEventListener('click', () => {
    document.body.classList.toggle("dark");
    button.classList.toggle("dark");
})

profileDiv = document.getElementById('ave')
imageExistenceStatus = true

profileDiv.addEventListener('click', )

function createImage(path){
    image = document.createElement('img');
    image.classList.add('profile-picture');
    image.src = `/${path}`;
    image.alt = 'profile-picture';

    return image
}

function choosePfp(path, imageExistenceStatus){
    if (imageExistenceStatus){
        existingImg = document.getElementsByClassName('profile-picture')
        existingImg.remove()
        img = createImage(path)
    }
    else{
        img = createImage(path)
    }
    profileDiv.append(img)
}

