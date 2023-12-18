const { createWriteStream } = require('fs');
const { promisify } = require('util');
const { join } = require('path');
const { default: axios } = require('axios');
const { createCanvas, loadImage, Image, registerFont } = require('canvas');
const { expand } = require('canvas-constructor/lib/Util');
const { text, drawImage } = require('canvas-constructor');

class Demotivator {
  constructor(topText = '', bottomText = '') {
    this._topText = topText;
    this._bottomText = bottomText;
  }

  async create(
    file,
    watermark = null,
    resultFilename = 'demresult.jpg',
    fontColor = 'white',
    fillColor = 'black',
    fontName = 'times.ttf',
    topSize = 80,
    bottomSize = 60,
    arrange = false,
    useUrl = false,
    deleteFile = false,
  ) {
    if (useUrl) {
      const { data } = await axios.get(file, { responseType: 'arraybuffer' });
      file = join(__dirname, 'demotivator_picture.jpg');
      await promisify(createWriteStream(file))(Buffer.from(data, 'binary'));
    }

    /*
      Создаем шаблон для демотиватора
      Вставляем фотографию в рамку
    */

    let userImg = await loadImage(file);
    let width, height;
    if (arrange) {
      ({ width, height } = userImg);
      width += 250;
      height += 260;
    } else {
      width = 1280;
      height = 1024;
    }
    const img = createCanvas(width, height);
    const imgBorder = createCanvas(width - 10, height - 10);
    const border = expand(imgBorder, 2, '#ffffff');
    const drawer = img.getContext('2d');

    if (arrange) {
      drawer.fillStyle = fillColor;
      drawer.fillRect(0, 0, width, height);
      drawer.drawImage(border, 111, 96);
      drawer.drawImage(userImg, 118, 103);
    } else {
      drawer.fillStyle = fillColor;
      drawer.fillRect(0, 0, width, height);
      drawer.drawImage(border, 111, 96);
      drawer.drawImage(userImg, 118, 103, 1050, 710);
    }

    /*
      Подбираем оптимальный размер шрифта
      Добавляем текст в шаблон для демотиватора
    */

    registerFont(join(__dirname, fontName), { family: 'Custom' });
    let font1 = `${topSize}px Custom`;
    let textWidth = drawer.measureText(this._topText).width;
    while (textWidth >= width - 20) {
      font1 = `${--topSize}px Custom`;
      drawer.font = font1;
      textWidth = drawer.measureText(this._topText).width;
    }
    let font2 = `${bottomSize}px Custom`;
    textWidth = drawer.measureText(this._bottomText).width;
    while (textWidth >= width - 20) {
      font2 = `${--bottomSize}px Custom`;
      drawer.font = font2;
      textWidth = drawer.measureText(this._bottomText).width;
    }
    drawer.fillStyle = fontColor;
    drawer.font = font1;
    const size1 = [drawer.measureText(this._topText).width, topSize];
    drawer.fillText(this._topText, (width - size1) / 2, 80);
    drawer.font = font2;
    const size2 = [drawer.measureText(this._bottomText).width, bottomSize];
    drawer.fillText(this._bottomText, (width - size2[0]) / 2, height - 50);
    /*
    Добавляем водяной знак, если он указан
    Сохраняем результат в файл
    */

    if (watermark) {
        const watermarkImg = await loadImage(watermark);
        drawer.drawImage(watermarkImg, 20, 20, 80, 80);
    }
    
    const stream = createWriteStream(resultFilename);
    const out = img.createJPEGStream({
        quality: 0.9,
        chromaSubsampling: true,
    });
    
    out.pipe(stream);
    await new Promise((resolve) => {
        out.on('end', resolve);
    });
    
    if (deleteFile && useUrl) {
        await promisify(unlink)(file);
    }
    
    return resultFilename;}
}

module.exports = Demotivator;
    