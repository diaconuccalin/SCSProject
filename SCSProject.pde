import processing.video.*;
import processing.sound.*;

boolean motionView = true;

Capture video;
PImage prev;

int pixelThreshold = 80;
int overallThreshold = 20;

SinOsc sine;

void captureEvent(Capture video) {
  prev.copy(video, 0, 0, video.width, video.height, 0, 0, prev.width, prev.height);
  prev.updatePixels();
  video.read();
}

void setup() {
  size(640, 480);

  video = new Capture(this, 640, 480);
  video.start();
  prev = createImage(video.width, video.height, RGB);

  sine = new SinOsc(this);
  sine.play();
  sine.freq(400);
}

void draw() {
  video.loadPixels();
  image(video, 0, 0);

  int difference = 0;

  if (motionView)
    loadPixels();

  for (int i = 0; i < video.width * video.height; i++) {
    color currentColor = video.pixels[i];
    float r1 = red(currentColor);
    float g1 = green(currentColor);
    float b1 = blue(currentColor);

    color prevColor = prev.pixels[i];
    float r2 = red(prevColor);
    float g2 = green(prevColor);
    float b2 = blue(prevColor);

    float d = dist(r1, g1, b1, r2, g2, b2);
    if (d>pixelThreshold) {
      if (motionView)
        pixels[i] = color(255);
      difference++;
    } else {
      if (motionView)
        pixels[i] = color(0);
    }
  }

  if (motionView)
    updatePixels();

  if (difference > overallThreshold) {
    println("INTRUDER!");

    if (((millis()/500)%2)==0) {
      sine.play();
    } else {
      sine.stop();
    }
  } else {
    sine.stop();
    println("NO INTRUDER.");
  }
}
